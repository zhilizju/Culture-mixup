import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests import Session


def read_source_concepts_from_excel(file_path):
    df = pd.read_excel(file_path)
    source_concepts = df['Concept'].tolist()
    source_concepts = [str(concept).lower() for concept in source_concepts if not pd.isna(concept)]
    # source_concepts = [str(concept) for concept in source_concepts if not pd.isna(concept)]
    return source_concepts
# source_concepts = [str(concept) for concept in source_concepts if not pd.isna(concept)]

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
   
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session