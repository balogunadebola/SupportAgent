import os
from dotenv import load_dotenv
from pathlib import Path

# Import Azure AI Foundry client libraries and custom user functions.
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, ToolSet
from SupportAgent.user_functions import user_functions

def main():
    """
    Main function to initialize the agent, connect with Azure AI Foundry,
    and handle interactive user input for support ticket submission.
    """
    # Clear the console for a clean interface.
    os.system('cls' if os.name == 'nt' else 'clear')

    # Load environment variables from the .env file.
    load_dotenv()
    PROJECT_CONNECTION_STRING = os.getenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
    MODEL_DEPLOYMENT = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

    # Create an Azure AI Foundry project client using the connection string and default Azure credentials.
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        conn_str=PROJECT_CONNECTION_STRING
    )
    
    # Use the client to create the agent and process runs.
    with project_client:
        # Create a function tool from the user-defined functions.
        functions = FunctionTool(user_functions)
        toolset = ToolSet()
        toolset.add(functions)
                
        # Create an AI agent with custom instructions.
        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT,
            name="support-agent",
            instructions=(
                "You are a technical support agent. When a user has a technical issue, obtain their email "
                "address and a description of the issue. Use the provided function to submit a support ticket. "
                "If a file is saved, inform the user of the file name."
            ),
            toolset=toolset
        )
        thread = project_client.agents.create_thread()
        print(f"You're chatting with: {agent.name} ({agent.id})")

        # Loop for user interaction.
        while True:
            user_prompt = input("Enter a prompt (or type 'quit' to exit): ")
            if user_prompt.lower() == "quit":
                break
            if not user_prompt.strip():
                print("Please enter a prompt.")
                continue

            # Create and process the user's message.
            project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_prompt
            )
            run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)

            # Check run status for any errors.
            if run.status == "failed":
                print(f"Run failed: {run.last_error}")
            
            # Retrieve and display the most recent assistant response.
            messages = project_client.agents.list_messages(thread_id=thread.id)
            last_msg = messages.get_last_text_message_by_role("assistant")
            if last_msg:
                print(f"Assistant: {last_msg.text.value}")

        # After quitting, print the conversation history.
        print("\nConversation Log:\n")
        messages = project_client.agents.list_messages(thread_id=thread.id)
        for message_data in reversed(messages.data):
            last_message_content = message_data.content[-1]
            print(f"{message_data.role}: {last_message_content.text.value}\n")

        # Clean up the created agent and thread.
        project_client.agents.delete_agent(agent.id)
        project_client.agents.delete_thread(thread.id)

if __name__ == '__main__':
    main()
