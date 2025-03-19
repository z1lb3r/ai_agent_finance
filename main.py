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

# Настройка логирования - перемещено в начало файла
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Импортируем регистр инструментов
from tools.registry import get_all_tools

# ВАЖНО: Сначала импортируем модули с инструментами, чтобы они могли зарегистрироваться
import tools.sec_downloader
import tools.pdf_analyzer

from agents import Runner, RunConfig
# Импортируем функцию для получения агента ПОСЛЕ регистрации инструментов
from agent import get_agent, model_settings

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
Type 'tools' to see available tools.
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
- 'tools': Show available tools
    """)
    print("-" * 80 + "\n")

def print_available_tools() -> None:
    """Print a list of available tools."""
    tools = get_all_tools()
    print("\n" + "-" * 80)
    print(f"{'AVAILABLE TOOLS':^80}")
    print("-" * 80)
    print(f"\nThe agent has access to {len(tools)} tools:\n")
    
    for i, tool in enumerate(tools, 1):
        if hasattr(tool, 'name'):
            tool_name = tool.name
            description = getattr(tool, 'description', '')
            print(f"{i}. {tool_name}")
            if description:
                # Ограничиваем длину описания для компактности
                if len(description) > 80:
                    description = description[:77] + "..."
                print(f"   {description}")
        else:
            print(f"{i}. [Unnamed Tool]")
    
    print("\n" + "-" * 80 + "\n")

def main() -> None:
    """Main application function."""
    try:
        # Выводим в лог количество найденных инструментов ПЕРЕД созданием агента
        tools = get_all_tools()
        logger.info(f"Found {len(tools)} registered tools")
        
        # Получаем агента (инициализируется при первом вызове)
        investment_agent = get_agent()
        
        # Создаем конфигурацию для выполнения
        run_config = RunConfig(
            tracing_disabled=True,
            workflow_name="Investment Analysis",
            model_settings=model_settings
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
            
            # Проверяем команду вывода доступных инструментов
            if user_input.lower() == 'tools':
                print_available_tools()
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
                print("Please try again with a different query.")
    
    except Exception as e:
        logger.exception("Fatal error in main loop")
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()