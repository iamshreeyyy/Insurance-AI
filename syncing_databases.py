import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import openai
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import json
import time
from threading import Timer, Event, Thread

# Set up OpenAI API key
openai.api_key = 'your_openai_api_key'
    
# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="admin ",
    host="localhost",
    port="5433"
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur=conn.cursor()

# Create a trigger function that sends a notification for any changes in a row
cur.execute("""
            CREATE OR REPLACE FUNCTION notify_insurance_policy_change() RETURNS TRIGGER AS $$
            BEGIN
            PERFORM pg_notify('insurance_policy_change',row_to_json(NEW::text);
            RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """)

# Create a trigger for INSERT, UPDATE, DELETE
cur.execute("""
            CREATE TRIGGER insurance_policy_change_trigger
            AFTER INSERT OR UPDATE OR DELETE ON insurance_policies
            FOR EACH ROW EXECUTE FUNCTION notify_insurance_policy_change();
            """)
conn.commit()

# Listen for notifications
cur.execute("Listen insurance_policy_change;")

# Connect to Milvus
connections.connect("default",host="localhost",port="19530")
collection=Collection("insurance_policy_embeddings")

# Listen to accumulate notifications
notifications=[]
# Event to stop the program
stop_event = Event()
def get_openai_embedding(text):
    response = openai.Embedding.create(
        input = text,
        model = "text-embedding-ada-002"
    )
    return response['date'][0]['embedding']

def process_notifications():
    global notifications
    if notifications:
        print(f"Processing {len(notifications)}")
        for notify in notifications:
            data = json.loads(notify.payload)

            # Extract relevant information
            record_id = data['id']
            text = f"{data['customer_name']} {data['policy_type']} {data.get('life_insurance_details','')} {data.get('home_insurance_details','')} {data.get('auto_insrance_details','')}"

            # Convert to embedding using OpenAI model
            embedding = get_openai_embedding(text)

            # Update Milvus delete old embedding and insert new embedding
            collection.delete(f"id=={record_id}")
            collection.insert([{"id":record_id,"embedding":embedding}])
            print(f"Updated embedding for recordID {record_id} in Milvus")
        # Clear the notifications list after processing
        notifications = []

    # Schedule the next batch processing
    Timer(5,process_notifications).start()

# Start the batch processing
process_notifications

print("Waiting for notifications on channel 'insurance_policy_change'....")

def listen_for_stop_command():
    while True:
        command = input()
        if command.lower() == "stop program":
            stop_event.set()
            break

# Start a thread to listen for the stop command
stop_thread = Thread(target=listen_for_stop_command)
stop_thread.start()

while not stop_event is set():
    conn.poll()
    while conn.notifies:
        notify = conn.notifies.pop(0)
        notifications.append(notify)

# Close connections
cur.close()
conn.close()
connections.disconnect("default")

print("Program stopped")