"""
Investment AI Agent - Main application entry point.

This script provides a simple command-line interface for interacting with the Investment Agent.
a1
"""

import os
import sys
import json
import logging
import traceback
import time
import openai
from typing import Dict, List, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Импортируем модули с инструментами, чтобы они могли зарегистрироваться
try:
    import tools.sec_downloader
    import tools.pdf_analyzer
    import tools.trade_tracker
    import tools.bank_rag_tools
    import tools.rag_analyzer
except ImportError as e:
    logger.warning(f"Не удалось импортировать модули инструментов: {str(e)}")

# Импортируем регистр инструментов
from tools.registry import get_all_tools

# Импортируем функцию для инициализации инструментов
from investment_agent import initialize_tools

# Импортируем нужные компоненты из agents SDK
from agents import Runner, RunConfig

# Импортируем функцию для получения агента
from investment_agent.agent import get_agent, model_settings

def get_local_agent():
    """
    Получает агента для локального использования, гарантируя,
    что он имеет доступ к правильному реестру инструментов.
    """
    # Инициализируем инструменты
    initialize_success = initialize_tools()
    logger.info(f"Tools initialization: {'success' if initialize_success else 'failed'}")
    
    # Проверяем, сколько инструментов в реестре
    tools = get_all_tools()
    logger.info(f"Tools in registry after initialization: {len(tools)}")
    
    # Получаем экземпляр агента
    agent = get_agent()
    
    # Если у агента нет инструментов, но они есть в реестре,
    # добавляем их вручную
    if hasattr(agent, 'tools') and not agent.tools and tools:
        # Обновляем инструменты агента
        agent.tools = tools
        logger.info(f"Manually added {len(tools)} tools to agent")
    
    return agent

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
- "Analyze bank stock JPM using the latest quarterly report"

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
        
        # Получаем агента с гарантированными инструментами
        investment_agent = get_local_agent()
        
        # Создаем конфигурацию для выполнения
        run_config = RunConfig(
            tracing_disabled=True,
            workflow_name="Investment Analysis"
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
                
                # Максимальное количество попыток
                max_retries = 3
                
                # Цикл повторных попыток при ошибке превышения лимита токенов
                for attempt in range(max_retries):
                    try:
                        # Выполняем запрос с учётом истории разговора
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
                        
                        # Если дошли до этой точки без ошибок, выходим из цикла
                        break
                            
                    except openai.RateLimitError as e:
                        # Если это последняя попытка, пробрасываем ошибку дальше
                        if attempt == max_retries - 1:
                            raise
                            
                        # Извлекаем рекомендуемое время ожидания из сообщения об ошибке
                        wait_time = 2  # По умолчанию 2 секунды
                        
                        error_message = str(e)
                        if "Please try again in" in error_message:
                            try:
                                wait_text = error_message.split("Please try again in")[1].split("s.")[0].strip()
                                wait_time = float(wait_text) + 1  # Добавляем секунду для надежности
                            except:
                                pass  # В случае ошибки парсинга используем значение по умолчанию
                                
                        # Сообщаем пользователю о задержке
                        print(f"\nДостигнут лимит запросов API. Ожидание {wait_time:.2f} секунд перед повторной попыткой ({attempt+1}/{max_retries})...")
                        
                        # Ждем указанное время
                        time.sleep(wait_time)
                        
                        # Продолжаем цикл для следующей попытки
                
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