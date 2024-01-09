# Culture-mixup

## To Do List

- [✓] **Upload Cultural Concepts Dataset**
   - Status: Completed
   - Description: The dataset, featuring cultural concepts from five different countries and regions, has been successfully uploaded. It provides detailed explanations and corresponding images.
   - Dataset Link: [https://huggingface.co/datasets/zhili312/multimodal-cultural-concepts](https://huggingface.co/datasets/zhili312/multimodal-cultural-concepts)

- [✓] **Upload Cultural Concepts Adaptation Dataset**
   - Status: Completed
   - Description: This dataset includes both the semantic relationships based on ConceptNet from the original paper and fuzzy searches conducted by ChatGPT.

- [✓] **Upload Cultural Concepts Adaptation Code**
   - Status: Completed
   - Description: The provided code can be used to replicate the above Cultural Concepts Adaptation Dataset and can also be applied to create general cultural concept adaptation datasets.
   - Usage Instructions:
     1. Install the necessary dependencies listed in `requirements.txt`.
     2. Download the Cultural Concepts Dataset.
     3. For example, to use Chinese as the source language, run the following command:
        ```
        python Buildgraph.py --source_language zh --target_language en --input_file Chinese/Chinese.xlsx --output_file Chinese_English_adaptation_with_chatgpt.xlsx --use_chatgpt
        ```

- [ ] **Upload Culture-mix Code**
   - Status: Coming Soon
  

- [ ] **Upload the Latest Multimodal Language Model (GPT-4-V and Minigpt-4) Test Dataset and Evaluation Results**
   - Status: Coming Soon
   



