import networkx as nx
import requests
import argparse
import openai
from openai import OpenAI
import pandas as pd
import os
from utils import read_source_concepts_from_excel,save_results_to_excel,get_language_full_name,requests_retry_session

os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

def read_source_concepts_from_excel(file_path):
    df = pd.read_excel(file_path)
    source_concepts = df['Concept'].tolist()
    source_concepts = [str(concept).lower() for concept in source_concepts if not pd.isna(concept)]
    return source_concepts

def save_results_to_excel(results, output_file):
    df = pd.DataFrame(results, columns=['Source Concept', 'Target Concept', 'Distance'])
    df.to_excel(output_file, index=False)
    
    
def get_language_full_name(language_abbr):
    # Mapping of language abbreviations to full names
    language_map = {
        'en': 'English',
        'zh': 'Chinese',
        'ta': 'Tamil',
        'tr': 'Turkish',
        'sw': 'Swahili',
        'id': 'Indonesian'
    }

    # Retrieve and return the full name of the language
    return language_map.get(language_abbr, "Unknown Language")    
    
 

class CulturalAdaptationGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def format_concept(self, concept):
        # Replace spaces with underscores
        return concept.replace(" ", "_")
    
    def format_language(self, concept):
        # Replace underscores with spaces
        return concept.replace("_", " ")
    
    def concept_exists_in_conceptnet(self, concept, language):
        formatted_concept = concept.replace(" ", "_")
        url = f'http://api.conceptnet.io/c/{language}/{formatted_concept}'
        
        try:
            response = requests_retry_session().get(url)
            if response.status_code == 200:
                data = response.json()
                return len(data.get('edges', [])) > 0
            else:
                print(f"Error occurred: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}")
            return False   
    


    def add_hypernyms(self, concept, language):
        # Add hypernyms (superordinate concepts)
        concept = self.format_concept(concept)
        url = f'http://api.conceptnet.io/query?start=/c/{language}/{concept}&rel=/r/IsA'
        try:
            response = requests.get(url).json()
            for edge in response['edges']:
                if edge['start']['label'].lower() == concept.lower():
                    hypernym = edge['end']['label']
                    self.graph.add_node(hypernym, language=language, type='hypernym')
                    self.graph.add_edge(concept, hypernym, relation='hypernym')
        except Exception as e:
            print(f"Error occurred while fetching hypernyms: {e}")

    def add_hyponyms(self, concept, target_language):
        # Fetch all relations of a concept, then filter for hyponyms (subordinate concepts)
        concept = self.format_concept(concept)
        concept_id = f'/c/{target_language}/{concept}'
        url = f'http://api.conceptnet.io/query?node={concept_id}&limit=1000'
        try:
            response = requests.get(url).json()
            for edge in response['edges']:
                # Check for hyponym relation, ensuring it's for the correct concept
                if edge['rel']['label'] == 'IsA' and edge['end']['@id'].lower() == concept_id:
                    hyponym_full_id = edge['start']['@id']
                    # Extract the actual concept part
                    hyponym = hyponym_full_id.split('/')[-1]
                    self.graph.add_node(hyponym, language=target_language, type='hyponym')
                    self.graph.add_edge(concept, hyponym, relation='hyponym')
        except Exception as e:
            print(f"Error occurred while fetching hyponyms: {e}")

    def add_translated_synonyms(self, concept, source_language, target_language):
        # Add synonyms in the target language
        concept = self.format_concept(concept)
        url = f'http://api.conceptnet.io/query?start=/c/{source_language}/{concept}&rel=/r/Synonym'
        try:
            response = requests.get(url).json()
            for edge in response['edges']:
                if edge['end']['language'] == target_language:
                    translated_synonym = edge['end']['label']
                    translated_synonym = self.format_concept(translated_synonym)
                    self.graph.add_node(translated_synonym, language=target_language, type='translated_synonym')
                    self.graph.add_edge(concept, translated_synonym, relation='translated_synonym')
        except Exception as e:
            print(f"Error occurred while fetching translated synonyms: {e}")

    def print_graph_info(self):
        print("Graph Information")
        print("=================")
        print(f"Number of nodes: {self.graph.number_of_nodes()}")
        print(f"Number of edges: {self.graph.number_of_edges()}")
        print("\nSample Nodes:")
        for node in list(self.graph.nodes())[:10]:
            print(f"Node: {node}, Edges: {list(self.graph.edges(node))[:10]}")     
            
    def calculate_distances_to_source(self, source_concept, target_language):
        distances = {}
        for node in self.graph.nodes:
            if self.graph.nodes[node].get('language') == target_language:
                try:
                    if source_concept in self.graph and node in self.graph:
                        # Calculate the distance from the source concept to each concept in the target language
                        distance = nx.shortest_path_length(self.graph, source=source_concept, target=node)
                        distances[node] = distance
                except nx.NetworkXNoPath:
                    # Ignore the node if no path exists
                    continue

        # Sort the distances
        sorted_distances = sorted(distances.items(), key=lambda x: x[1])
        return sorted_distances

    
    
    def call_chatgpt_for_cultural_adaptation(self, concept, source_language, target_language, model="gpt-4", max_tokens=150):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is not set in environment variables")

        client = OpenAI(api_key=api_key)
        
        source_language_full=get_language_full_name(source_language)
        target_language_full=get_language_full_name(target_language)
        
        prompt=f"List up to 10 common {target_language_full} concepts from Western culture that can be analogously used to explain the {source_language_full} concept '{concept}'. Only list the concepts themselves, without explanations. Separate each concept with a newline."

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message
        except Exception as e:
            raise Exception(f"Error in calling OpenAI API: {e}")

            
    def add_generated_concepts_to_graph(self, source_concept, response, target_language):
        concepts = response.content.split('\n')
        for concept in concepts:
            if concept.strip():
               
                concept_clean = concept.split('. ', 1)[-1].strip()
                self.graph.add_node(concept_clean, language=target_language)
                self.graph.add_edge(source_concept, concept_clean, relation='cultural_adaptation')



        
    def run(self, source_concept, source_language, target_language, use_chatgpt):
        # Check if the source concept exists in ConceptNet
        concept_found = self.concept_exists_in_conceptnet(source_concept, source_language)
        
        if concept_found:
            # Add translated synonyms for the source concept
            self.add_translated_synonyms(source_concept, source_language, target_language)

            # Add hypernyms for the source concept (first-order)
            self.add_hypernyms(source_concept, source_language)

            # Process each first-order hypernym
            if source_concept in self.graph:
                for hypernym in list(self.graph.successors(source_concept)):
                    if self.graph.nodes[hypernym].get('type') == 'hypernym':
                        self.add_translated_synonyms(hypernym, source_language, target_language)
                        for translated_concept in list(self.graph.successors(hypernym)):
                            if self.graph.nodes[translated_concept].get('type') == 'translated_synonym':
                                self.add_hyponyms(translated_concept, target_language)
                        


                        # Add hypernyms for this hypernym （two-order）
                        self.add_hypernyms(hypernym, source_language)

                        
                        # Process each second-order hypernym
                        for second_order_hypernym in list(self.graph.successors(hypernym)):
                            if self.graph.nodes[second_order_hypernym].get('type') == 'hypernym':
                                self.add_translated_synonyms(second_order_hypernym, source_language, target_language)
                                for translated_concept in list(self.graph.successors(second_order_hypernym)):
                                    if self.graph.nodes[translated_concept].get('type') == 'translated_synonym':
                                        self.add_hyponyms(translated_concept, target_language)

                                    # Process each hyponym of the second-order hypernym
                                    for one_order_hyponym in list(self.graph.successors(translated_concept)):
                                        if self.graph.nodes[one_order_hyponym].get('type') == 'hyponym':
                                            # Add hyponyms of the hyponym (third-order)
                                            self.add_hyponyms(one_order_hyponym, target_language)
                
                # For those without hypernyms in the source language, use synonyms in the target language to construct [the graph].         
                for translated_synonym in list(self.graph.successors(source_concept)):
                    if self.graph.nodes[translated_synonym].get('type') == 'translated_synonym':
                    
                        # Add hypernyms for this translated_synonym
                        self.add_hypernyms(translated_synonym, target_language)
                        for hypernym in list(self.graph.successors(translated_synonym)):
                            if self.graph.nodes[hypernym].get('type') == 'hypernym':
                                self.add_hyponyms(hypernym, target_language)
                 
                                        
                print("source_concept:",source_concept)
                print("Exist")

        else:
            print("source_concept:",source_concept)
            print("No exist")

                
        if not concept_found and use_chatgpt:
            response = self.call_chatgpt_for_cultural_adaptation(source_concept, source_language, target_language)
            self.add_generated_concepts_to_graph(source_concept, response, target_language)
          
        
        
        self.print_graph_info()

        # Calculate and sort distances
        sorted_distances = self.calculate_distances_to_source(source_concept, target_language)
        for concept, distance in sorted_distances:
            print(f"Distance from '{source_concept}' to '{concept}': {distance}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cultural Adaptation Graph Builder")
    # parser.add_argument("--source_concept", type=str, help="The source concept")
    parser.add_argument("--source_language", type=str, help="The source language")
    parser.add_argument("--target_language", type=str, help="The target language")
    parser.add_argument("--use_chatgpt", action='store_true', help="Use ChatGPT for fuzzy matching when a concept is not found in ConceptNet")
    parser.add_argument("--input_file", type=str, help="Path to the input Excel file with source concepts")
    parser.add_argument("--output_file", type=str, default="output.xlsx", help="Path to the output Excel file for results")

    args = parser.parse_args()

    source_concepts = read_source_concepts_from_excel(args.input_file)
    
    all_results = []

    for source_concept in source_concepts:
        cultural_graph = CulturalAdaptationGraph()
        cultural_graph.run(source_concept, args.source_language, args.target_language, args.use_chatgpt)
        distances = cultural_graph.calculate_distances_to_source(source_concept, args.target_language)

        for target_concept, distance in distances:
            all_results.append((source_concept, target_concept, distance))

            

    save_results_to_excel(all_results, args.output_file)
    