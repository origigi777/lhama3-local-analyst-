# lhama3-local-analyst-
Ask Questions in Hebrew about CSV Files – Fully Offline
This system allows users to upload a local CSV file and ask free-form questions in Hebrew without requiring any external API everything runs locally.

Project Description
This project is designed for users who want to analyze and explore CSV data using natural Hebrew questions without sending the data over the internet. the user uploads a csv file to the model, the model get the data and then you can ask the bot any questions on your data fully local!

Suitable Use Cases
Research or data analysis questions  of any CSV files
Privacy-sensitive environments with no internet access
Easy integration of local NLP into existing apps
Useful for data analysts, researchers, and students
System Requirements
Python 3.8+

Node.js and a modern web browser (for the frontend)

Local language model such as lhama3 

Main Python libraries:

sentence-transformers
fastapi
pandas
scikit-learn
uvicorn
fastapi.middleware.cors for CORS support
Frontend: basic HTML/JavaScript (no frameworks needed)

Installation
Install Python dependencies:
pip install -r requirements.txt

Run the local backend server:
uvicorn server:app --host 0.0.0.0 --port 8080

Open index.html file in your browser.
Usage Example
Upload a CSV file with Hebrew/English content.

Once loaded, type a question like:

"Which student got the highest grade?"
"How many products were sold in March?"
"What is the name of the employee who got the highest bonus?"
The system will analyze the data and return the most relevant answer.

Architecture Overview
Frontend: Simple HTML/JavaScript interface to upload CSV and send questions
Backend: Fastserver that processes the data, generates embeddings, and compares the user question to the dataset- python interface for fester respond and make the model use pandas alone without any user knolage requiring 
Embedding Model: Uses a Hebrew/English -compatible model to vectorize questions and rows, comparing them via cosine similarity


in terminal located to backand folder run the command:

 python3 app.py

 

