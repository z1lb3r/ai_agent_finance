"""
Investment AI Agent - Main application entry point.

This script provides a simple command-line interface for interacting with the Investment Agent.
"""

import os
import sys
import json
import logging
import traceback
from typing import Dict, List, Any, Optional

from agents import Runner, RunConfig
from agent import investment_agent

def print_welcome() -> None:
    """Print a welcome message."""
    print("\n" + "=" * 80)
    print(f"{'Investment AI Agent':^80}")
    print("=" * 80)
    print("""
This AI agent can help you with financial market analysis, company information, 
and investment insights. It uses SEC EDGAR data to provide reliable information
about publicly traded companies.

Type 'exit', 'quit', or 'q' to end the session.
Type 'clear' to start a new conversation.
Type 'help' for more information.
    """)
    print("-" * 80 + "\n")

def print_help() -> None:
    """Print help information."""
    print("\n" + "-" * 80)
    print(f"{'HELP INFORMATION':^80}")
    print("-" * 80)
    print("""
Example queries:
- "What is the market outlook today?"
- "Tell me about Apple Inc. (AAPL)"
- "Compare the financials of Microsoft (MSFT) and Google (GOOGL)"
- "What are the recent SEC filings for Tesla (TSLA)?"
- "Explain the key financial metrics for Amazon (AMZN)"

Commands:
- 'exit', 'quit', or 'q': End the session
- 'clear': Start a new conversation
- 'help': Display this help information
    """)
    print("-" * 80 + "\n")

def main() -> None:
    """Main application function."""
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("main")
    
    try:
        # Создаем конфигурацию для выполнения
        run_config = RunConfig(
            tracing_disabled=True,  # Отключаем трассировку
            workflow_name="Investment Analysis",
        )
        
        # Хранение истории разговора
        conversation_context = []
        
        # Выводим приветствие
        print_welcome()
        
        # Главный цикл общения
        while True:
            # Получаем ввод пользователя
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting Investment AI Agent. Goodbye!")
                break
            
            # Проверяем команды выхода
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nExiting Investment AI Agent. Goodbye!")
                break
            
            # Проверяем команду очистки истории
            if user_input.lower() == 'clear':
                conversation_context = []
                print("\nConversation history cleared. Starting a new conversation.")
                continue
            
            # Проверяем команду помощи
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Пропускаем пустой ввод
            if not user_input:
                continue
            
            # Обрабатываем запрос пользователя
            try:
                print("\nThinking...\n")
                
                # Если есть история разговора, включаем её
                if conversation_context:
                    input_with_context = conversation_context + [{"role": "user", "content": user_input}]
                    response = Runner.run_sync(
                        investment_agent, 
                        input_with_context,
                        run_config=run_config
                    )
                else:
                    # Первое сообщение в разговоре
                    response = Runner.run_sync(
                        investment_agent, 
                        user_input,
                        run_config=run_config
                    )
                
                # Обновляем историю разговора
                if not conversation_context:
                    conversation_context = [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": response.final_output}
                    ]
                else:
                    conversation_context.append({"role": "user", "content": user_input})
                    conversation_context.append({"role": "assistant", "content": response.final_output})
                
                # Выводим ответ агента
                print(f"Agent: {response.final_output}\n")
                
            except Exception as e:
                logger.exception("Error processing query")
                print(f"\nError: {str(e)}\n")
                traceback.print_exc()
                print("Please try again with a different query.")
    
    except Exception as e:
        logger.exception("Fatal error in main loop")
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()