import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
import warnings
import json
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
import os
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel
from langchain_groq import ChatGroq
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.messages import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.utilities import SQLDatabase
import pytz
import sqlite3
import tqdm
import threading
import time
import requests


os.environ["GROQ_API_KEY"] = "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"

warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community")

tagging_prompt = ChatPromptTemplate.from_template(
    """
    Extract the desired information from the following passage.

    Only extract the properties mentioned in the 'Classification' function.

Check Reminder
Input: When do I need to submit the assignment tomorrow? Output: check reminder
Input: What time should I wake up tomorrow? Output: check reminder
Input: When is my next meeting? Output: check reminder
Input: What's my plan for the evening? Output: check reminder
Input: Can you tell me if I have any appointments today? Output: check reminder
Input: What time is my dentist appointment? Output: check reminder
Input: Do I have any reminders set for tomorrow? Output: check reminder
Input: When do I need to pick up the dry cleaning? Output: check reminder
Input: What is the time for my call with John? Output: check reminder
Input: Do I have any meetings scheduled for today? Output: check reminder

Set Reminder
Input: Remind me to call mom at 3 PM today. Output: set reminder
Input: Schedule a reminder for my meeting at 10 AM. Output: set reminder
Input: Set a reminder to water the plants every Saturday. Output: set reminder
Input: Remind me to finish my report by 5 PM today. Output: set reminder
Input: Create a reminder for my friend’s birthday tomorrow. Output: set reminder
Input: Set a reminder to buy groceries this evening. Output: set reminder
Input: Schedule a reminder to check the mail. Output: set reminder
Input: Remind me to call the vet on Monday. Output: set reminder
Input: Create a reminder to pick up the package at 4 PM. Output: set reminder
Input: Set a reminder to attend the webinar at noon. Output: set reminder

Update Reminder
Input: Update the reminder for the meeting. Output: update reminder
Input: Change the reminder time to 2 PM for the call. Output: update reminder
Input: Modify the reminder for picking up the dry cleaning to next week. Output: update reminder
Input: Adjust the reminder for the dentist appointment to 11 AM. Output: update reminder
Input: Update my reminder for the project deadline to next Friday. Output: update reminder
Input: Change the reminder to water the plants to every other day. Output: update reminder
Input: Update the reminder to finish the report to 6 PM. Output: update reminder
Input: Adjust the reminder for the birthday party to 6 PM. Output: update reminder
Input: Modify the reminder to call the vet to next Tuesday. Output: update reminder
Input: Update the reminder for the webinar to 1 PM. Output: update reminder

Remove Reminder
Input: Remove my reminder about buying groceries. Output: remove reminder
Input: Delete the reminder for the dentist appointment. Output: remove reminder
Input: Remove the reminder to water the plants. Output: remove reminder
Input: Erase the reminder for the meeting at 10 AM. Output: remove reminder
Input: Delete the reminder to pick up the package. Output: remove reminder
Input: Remove the reminder for calling mom. Output: remove reminder
Input: Erase the reminder for the report deadline. Output: remove reminder
Input: Remove my reminder about the friend's birthday. Output: remove reminder
Input: Delete the reminder for checking the mail. Output: remove reminder
Input: Remove the reminder for the webinar. Output: remove reminder

Other Content
Input: I will be busy this weekend. Output: other content
Input: I have a free day tomorrow. Output: other content
Input: I’m planning to relax this evening. Output: other content
Input: I’m feeling tired today. Output: other content
Input: I need to buy a new book. Output: other content
Input: I want to learn a new skill. Output: other content
Input: I’m interested in starting a new hobby. Output: other content
Input: I need to schedule some time for exercise. Output: other content
Input: I have a lot of work to do this week. Output: other content
Input: I’m thinking of going on vacation next month. Output: other content

    Training data for reference:
    {traning_data}

    Passage:
    {input}
    """
)


class Classification(BaseModel):
    sentiment: str = Field(..., enum=["set reminder", "update reminder", "check reminder", "remove reminder", "other content"])


llm = ChatGroq(model="gemma2-9b-it", temperature=0).with_structured_output(Classification)
llm_chat = ChatGroq(model="gemma2-9b-it", temperature=0)

tagging_chain = tagging_prompt | llm

def get_current_time():
    adelaide_tz = pytz.timezone('Australia/Adelaide')
    now = datetime.now(adelaide_tz)
    return now.strftime("%I:%M:%S %p")  # Returns time in HH:MM:SS format

def get_date():
    adelaide_tz = pytz.timezone('Australia/Adelaide')
    current_date = datetime.now(adelaide_tz).strftime("%Y-%m-%d")
    return current_date

def create_reminders_table():
    sql_statement = """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            time TEXT NOT NULL,
            date TEXT,
            reason TEXT NOT NULL,
            frequency TEXT NOT NULL,
            days_of_week TEXT,
            status TEXT NOT NULL
        );
    """

    try:
        with sqlite3.connect('reminders.db') as conn:
            cursor = conn.cursor()
            cursor.execute(sql_statement)
            conn.commit()
            print("sucess")
    except sqlite3.Error as e:
        print(e)

create_reminders_table()

llm_st = ChatGroq(model="llama-3.1-70b-versatile", temperature=0)

prompt_st = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the text and only use the format given. "
        ),
        (
            "human", """
            User Input: {user_input}
            
                        
Instructions:

- **No Date or Day Specified:**
  - Assumption: Assume the reminder is for today.
  - Example: If the user says, "Remind me to call mom," and no specific date is given, the reminder should be set for today’s date ({current_date}).

- **No Time Specified:**
  - Assumption: Assume the current time is {time_now}.
  - Example: If the user says, "Remind me to start work," and no specific time is given, use the current time (e.g., 14:00:00) for the reminder.

- **24-Hour Format for Time:**
  - Handling Time Phrases:
    - If the user says "one hour later": Add one hour to the current time.
      - Example: If the current time is 14:00:00, "one hour later" means 15:00:00.
    - If the user says "in 30 minutes": Add 30 minutes to the current time.
      - Example: If the current time is 14:00:00, "in 30 minutes" means 14:30:00.

- **Day References:**
  - If the user says "tomorrow": Add one day to the current date.
    - Example: If today’s date is 2024-08-31 and the user says "tomorrow," the date for the reminder should be 2024-09-01.

- **Avoid Explaining:**
  - Direct Approach: Only provide the extracted details and the reminder alert without additional explanation.

- **Past Reminders:**
  - Handling Past Times:
    - Ensure: Reminders should only be set for the present or future. If the specified time and date are in the past, at the past question reply yes!
    - Example: If a reminder is for "one hour ago," or a date that has already passed, at "Is the time or date in past?" reply yes.

            """
        ),
    ]
)

import ast

# Model for reminders with validation to ensure days_of_week is always a list
class SetReminder(BaseModel):
    reason: str = Field(..., description="Reason of the reminder")
    time: str = Field(..., description="What time is the reminder set for? Format: 'hour:minute:second'")
    date: Optional[str] = Field(None, description="What date is the reminder set for? Format: 'Year-month-day'")
    frequency: str = Field(..., description="Is it asking for recurrence or not? Reply yes or no")
    days_of_week: Optional[List[str]] = Field(None, description="Days of the week for the reminder. Format: ['Monday', 'Wednesday'])")
    past: str = Field(..., description="Is the time or date in past? Reply yes or no")

    @validator("days_of_week", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            try:
                # Parse the string into a list if it's a string representation of a list
                v = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                # If it's just a single day in string form
                v = [v]
        return v

def save_reminder(reason, time, date, frequency, days_of_week):
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()

    # Convert days_of_week list to a comma-separated string
    days_of_week_str = ','.join(days_of_week) if days_of_week else None

    # Insert the reminder into the table
    c.execute('''
        INSERT INTO reminders (reason, time, date, frequency, days_of_week, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (reason, time, date, frequency, days_of_week_str, "active"))

    conn.commit()

    c.execute('SELECT * FROM reminders ORDER BY id DESC LIMIT 1')
    saved_reminder = c.fetchone()

    conn.close()

    print(f"Saved Reminder: {saved_reminder}")

    conn.close()


# Load the check_reminder data
with open("important_classification_data.json", 'r') as f:
    important_classification_data = json.load(f)

# Convert the intent classification data into Document format
docs = [Document(page_content=data["input"], metadata={"intent": data["intent"]}) for data in important_classification_data]

# Split the documents into smaller chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)

vectorstore = Chroma.from_documents(documents=splits, embedding=HuggingFaceEmbeddings())

# Set up the retriever to fetch relevant phrases based on the user's query
retriever = vectorstore.as_retriever()

def ensure_inactive_table():
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inactive_reminders (
            id INTEGER PRIMARY KEY,
            time TEXT,
            date TEXT,
            reason TEXT,
            frequency TEXT,
            days_of_week TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    print("Created!")
    conn.close()

ensure_inactive_table()

def check_upcoming_reminders():
    while True:
        conn = sqlite3.connect('reminders.db')
        c = conn.cursor()

        # Get the current date and time as a datetime object
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        current_day_of_week = current_time.strftime("%A")

        # Define a time window for checking reminders (e.g., 30 seconds before and after)
        time_window_start = (current_time - timedelta(seconds=30)).strftime("%H:%M:%S")
        time_window_end = (current_time + timedelta(seconds=30)).strftime("%H:%M:%S")

        # Check for reminders that are due today or on a specific date
        c.execute('''
            SELECT * FROM reminders
            WHERE (date = ? OR days_of_week LIKE ?)
            AND time BETWEEN ? AND ?
            AND status = 'active'
        ''', (current_date, f"%{current_day_of_week}%", time_window_start, time_window_end))

        upcoming_reminders = c.fetchall()

        for reminder in upcoming_reminders:
            print(f"Reminder Alert: {reminder[1]} at {reminder[2]} - {reminder[3]}")

            c.execute('''
                INSERT INTO inactive_reminders (time, date, reason, frequency, days_of_week, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (reminder[1], reminder[2], reminder[3], reminder[4], reminder[5], 'inactive'))
            conn.commit()
            print("Added inactive!")

            # Delete the reminder from the active reminders table
            c.execute('''
                DELETE FROM reminders WHERE id = ?
            ''', (reminder[0],))
            
            conn.commit()
            print("Deleted!")


        conn.close()

        # Check every 10 seconds
        time.sleep(10)


        
# Start the background thread to check for reminders
reminder_thread = threading.Thread(target=check_upcoming_reminders)
reminder_thread.daemon = True
reminder_thread.start()

message_max = """
Answer this question using the database provided only.

{question}

This is today's date: {date_tt}. So if user says Today it means the date of today!
tmr = tommorow

Database:
{context}

Only reply in this format, follow my instructions!

If no reminder is set on the day user requested, reply with: "No reminder found on that day."

If a reminder is found:
- Directly reply with the specific action and time, e.g., "You need to sleep at 10pm tomorrow."

Avoid providing additional context or listing all reminders unless user asked for!
"""

message_max = ChatPromptTemplate.from_messages([("human", message_max)])

rag_chain = message_max | llm_chat

def get_reminders():
    sql_statement = "SELECT * FROM reminders;"

    try:
        with sqlite3.connect('reminders.db') as conn:
            cursor = conn.cursor()
            cursor.execute(sql_statement)
            rows = cursor.fetchall()
            return rows
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return []

def format_reminders_for_context(reminders):
    context = ""
    for reminder in reminders:
        context += f"ID: {reminder[0]}, Time: {reminder[1]}, Date: {reminder[2]}, Reason: {reminder[3]}, Frequency {reminder[4]}, days_of_week: {reminder[5]}\n"
    return context


message_remove = """
Analyze the user's input and identify the reminder they want to remove from the database.

User input: {user_input}

Today's date is: {date_tt}. The current time is: {time_now}.

Use the following database context to identify the reminder:
{context}

If the reminder matches the user's input, respond with then requested reminder's id
Only integer!
Format: 
ID
Avoid reply:
ID: 3
Do Reply:
3

If no reminder matches, respond with "No matching reminder found."
"""
prompt_remove = ChatPromptTemplate.from_messages([("human", message_remove)])

rag_remove = prompt_remove | llm_chat

def remove_reminder_by_id(reminder_id):
    conn = sqlite3.connect('reminders.db')
    c = conn.cursor()

    # Fetch the reminder based on the given ID
    c.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
    reminder = c.fetchone()

    if reminder:
        # Move the reminder to the inactive_reminders table before deleting
        c.execute('''
            INSERT INTO inactive_reminders (time, date, reason, frequency, days_of_week, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (reminder[1], reminder[2], reminder[3], reminder[4], reminder[5], 'inactive'))
        conn.commit()

        # Delete the reminder from the active reminders table
        c.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        conn.commit()

        conn.close()
        print(f"Reminder with ID {reminder_id} removed successfully.")
    else:
        conn.close()
        print(f"No reminder found with ID {reminder_id}.")


message_sec = """
Answer this question using the database provided only.

{question}

This is today's date: {date_tt}. So if user says "today," it means the date of today!

Database sqlite:
{context}

Find the reminder that matches the criteria provided by the user. Generate an SQL query to update only the fields the user has requested to change. 

**Important:** 
- Retain existing values for fields not explicitly mentioned by the user.
- Time should always be in 24-hour format.

The SQL query should follow this format:

Dont change the date or other things if user doesnt requested for it, only changed what user asked for!

Example:
If the user requests to update the time to 11 PM today:
UPDATE reminders
SET date = "2024-09-01" AND time = "23:00:00" AND reason = "sleep" AND frequency = "no" AND days_of_week = "None";
WHERE date = "2024-09-01" AND time = "22:00:00" AND reason = "sleep" AND frequency = "no" AND days_of_week = "None";

If no reminder matches the criteria or no changes are requested, reply with "reminder_x"

Avoid providing additional context or listing all reminders.
"""



prompt_one = ChatPromptTemplate.from_messages([("human", message_sec)])

rag_chaining = prompt_one | llm_chat

llm = ChatGroq(model="llama-3.1-70b-versatile")

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community")

def get_session_history(user_id: str, conversation_id: str):
    connection = f"sqlite:///memory.db"
    return SQLChatMessageHistory(f"{user_id}--{conversation_id}", connection)


prompt_chat = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an friendly Ai Assitants Bot. Today date is {today_date}. Time now is {time_now}. Try having simple conversation unless user requested for some complex and long conversation.",
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ]
)

runnable_ch = prompt_chat | llm

with_message_history = RunnableWithMessageHistory(
    runnable_ch,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
    history_factory_config=[
        ConfigurableFieldSpec(
            id="user_id",
            annotation=str,
            name="User ID", #user_id
            description="Unique identifier for the user.",
            default="",
            is_shared=True,
        ),
        ConfigurableFieldSpec(
            id="conversation_id",
            annotation=str,
            name="Conversation ID", #session
            description="Unique identifier for the conversation.",
            default="",
            is_shared=True,
        ),
    ],
)

def get_ai_response(user_input):

    # If not found in examples, proceed with the existing AI logic
    try:
        response = ""
        for s in with_message_history.stream(
            {"input": user_input, "time_now": get_current_time(), "today_date": get_date()},
            config={"user_id": "123", "conversation_id": "1"}
        ):
            response += s.content
        return response, None
    except Exception as e:
        error_message = f"Error: {e}"
        return response, error_message

runnable_st = prompt_st | llm_st.with_structured_output(schema=SetReminder)
# Loop for continuous interaction

from typing import Dict

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class InputData(BaseModel):
    input: str

@app.post("/api/process")
async def process_input(data: InputData):
    user_input = data.input
    time_now = get_current_time()
    current_date = get_date()

    sentimenttocheck = ""
    res = tagging_chain.invoke({"input": user_input, "traning_data": retriever})
    sentimenttocheck += res.sentiment
    if sentimenttocheck == "set reminder":

            response = runnable_st.invoke({"user_input": user_input, "time_now": time_now, "current_date": current_date})

            save_reminder(response.reason, response.time, response.date, response.frequency, response.days_of_week)

            print(response.reason, response.time, response.date, response.frequency, response.days_of_week, response.past)

    elif sentimenttocheck == "update reminder":
            reminders_sec = get_reminders()
            database_sec = format_reminders_for_context(reminders_sec)
            updated_remind = ""
            for updated_cont in rag_chaining.stream({"question": user_input, "context": database_sec, "date_tt": get_date()}):
                updated_remind += updated_cont.content
            
            if updated_remind == "reminder_x":
                print("No reminder found to change!")
            else:
                try:
                    with sqlite3.connect('reminders.db') as conn:
                        cursor = conn.cursor()
                        cursor.execute(updated_remind)
                        conn.commit()
                    
                    if cursor.rowcount > 0:
                        print("Reminder updated successfully.")
                    else:
                        print("No reminder found to update with the given details.")
                        
                except sqlite3.Error as e:
                    print(f"Database error: {e}")

            print(f"Database: {updated_remind}")
    elif sentimenttocheck == "check reminder":
            reminders = get_reminders()
            database = format_reminders_for_context(reminders)
            response_max = ""
            for max in rag_chain.stream({"question": user_input, "context": database, "date_tt": get_date()}):
                response_max += max.content
            print(f"Database remind: {response_max}")
    elif sentimenttocheck == "remove reminder":
                # Fetch current reminders to provide context to the AI
            reminders = get_reminders()
            database_context = format_reminders_for_context(reminders)
            ai_response_rem = ""
    
            for max_rem in rag_remove.stream({"user_input": user_input, "context": database_context, "date_tt": current_date, "time_now": time_now}):
                ai_response_rem += max_rem.content

            remove_reminder_by_id(ai_response_rem)

            # Check if the AI found a matching reminder
            if "No matching reminder found" in ai_response_rem:
                print(ai_response_rem)

    else:
            ai_response_hi, error_message = get_ai_response(user_input)
            bot_response = f"AI: {ai_response_hi}"
    # Echo the input with "Bot: " prefix
    return {"response": bot_response}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)


