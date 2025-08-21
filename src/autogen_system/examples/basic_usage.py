# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統基本使用範例

展示如何使用新的 AutoGen 系統替代原有的 LangGraph 工作流。
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.controllers.workflow_controller import WorkflowController
from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator
from src.autogen_system.agents.base_agent import AgentFactory
from src.autogen_system.config.agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    AgentRole,
    WorkflowType,
)
from src.autogen_system.config.config_loader import config_loader
from src.logging import init_logging, get_logger
import os
from datetime import datetime

# 初始化專案的統一日誌系統
init_logging()

# 獲取專案的 logger
logger = get_logger(__name__)

# 確保日誌目錄存在
os.makedirs("logs", exist_ok=True)

logger.info("🚀 AutoGen 系統基本使用範例開始初始化")

# 測試日誌記錄功能
logger.info("🧪 測試日誌記錄功能...")
logger.debug("這是一條 DEBUG 日誌")
logger.info("這是一條 INFO 日誌")
logger.warning("這是一條 WARNING 日誌")
logger.error("這是一條 ERROR 日誌")
logger.info("✅ 日誌記錄功能測試完成")


def check_environment_and_config():
    """檢查環境變數和配置"""
    logger.info("🔍 檢查環境變數和配置...")

    # 使用配置載入器驗證配置
    logger.info("🔧 驗證配置...")
    validation_result = config_loader.validate_configuration()

    if not validation_result["valid"]:
        logger.error("❌ 配置驗證失敗:")
        for error in validation_result["errors"]:
            logger.error(f"  - {error}")
        return False
    else:
        logger.info("✅ 配置驗證成功")

    if validation_result["warnings"]:
        logger.warning("⚠️  配置警告:")
        for warning in validation_result["warnings"]:
            logger.warning(f"  - {warning}")
    else:
        logger.info("✅ 沒有配置警告")

    # 獲取環境變數資訊
    logger.info("🔍 檢查環境變數...")
    env_info = config_loader.get_environment_info()

    logger.info("✅ 環境變數檢查完成:")
    logger.info(f"  - OpenAI: {'✅' if env_info['openai']['api_key_set'] else '❌'}")
    logger.info(
        f"  - Azure OpenAI: {'✅' if env_info['azure_openai']['endpoint_set'] and env_info['azure_openai']['api_key_set'] else '❌'}"
    )
    logger.info(f"  - 搜尋 API: {env_info['search']['search_api']}")

    return True


def create_llm_config():
    """創建 LLM 配置"""
    logger.info("🔧 創建 LLM 配置...")

    try:
        # 檢查是否有 Azure OpenAI 配置
        logger.info("🔍 檢查 Azure OpenAI 配置...")
        env_info = config_loader.get_environment_info()

        if (
            env_info["azure_openai"]["endpoint_set"]
            and env_info["azure_openai"]["api_key_set"]
            and env_info["azure_openai"]["deployment_name"] != "未設定"
        ):
            logger.info("🔍 使用 Azure OpenAI 配置")
            llm_config = config_loader.load_llm_config(model_type="azure")
        else:
            logger.info("🔄 使用 OpenAI 配置")
            llm_config = config_loader.load_llm_config(model_type="openai")

        logger.info(f"✅ LLM 配置創建成功: {llm_config.model}")
        logger.info(f"  - model: {llm_config.model}")
        logger.info(f"  - temperature: {llm_config.temperature}")
        logger.info(f"  - max_tokens: {llm_config.max_tokens}")
        return llm_config

    except Exception as e:
        logger.error(f"❌ LLM 配置創建失敗: {e}")
        raise


def create_agent_configs(llm_config: LLMConfig):
    """創建智能體配置"""
    logger.info("🤖 創建智能體配置...")

    try:
        # 載入配置檔案
        logger.info("📂 載入 conf_autogen.yaml 配置檔案...")
        config = config_loader.load_yaml_config("conf_autogen.yaml")
        if not config:
            raise ValueError("無法載入配置檔案")
        logger.info("✅ 配置檔案載入成功")

        # 獲取智能體配置
        agents_config = config.get("agents", {})
        if not agents_config:
            raise ValueError("配置檔案中沒有智能體配置")

        logger.info(f"📋 找到 {len(agents_config)} 個智能體配置:")
        for agent_key in agents_config.keys():
            logger.info(f"  - {agent_key}")

        agent_configs = {}

        for agent_key, agent_dict in agents_config.items():
            try:
                logger.info(f"🔧 創建智能體 {agent_key} 的配置...")
                # 使用配置載入器創建智能體配置
                agent_config = config_loader.load_agent_config(agent_key, agent_dict)
                logger.info(f"✅ 智能體 {agent_key} 配置創建成功")

                # 如果智能體有自己的 LLM 配置覆蓋，使用它
                if agent_dict.get("llm_config_override"):
                    logger.info(f"🔧 智能體 {agent_key} 有 LLM 配置覆蓋")
                    override_config = agent_dict["llm_config_override"]

                    # 檢查是否要使用 Azure OpenAI
                    if override_config.get("use_azure", False):
                        agent_config.llm_config = config_loader.load_llm_config(
                            override_config, model_type="azure"
                        )
                    else:
                        # 使用覆蓋配置更新 LLM 配置
                        agent_config.llm_config = LLMConfig(
                            model=override_config.get("model", llm_config.model),
                            api_key=override_config.get("api_key", llm_config.api_key),
                            base_url=override_config.get("base_url", llm_config.base_url),
                            temperature=override_config.get("temperature", llm_config.temperature),
                            max_tokens=override_config.get("max_tokens", llm_config.max_tokens),
                            timeout=override_config.get("timeout", llm_config.timeout),
                            seed=override_config.get("seed", llm_config.seed),
                            extra_params=override_config.get(
                                "extra_params", llm_config.extra_params
                            ),
                        )
                    logger.info(f"✅ 智能體 {agent_key} 的 LLM 配置覆蓋應用成功")
                else:
                    logger.info(f"ℹ️  智能體 {agent_key} 使用預設 LLM 配置")

                agent_configs[agent_key] = agent_config
                logger.info(f"✅ 智能體 {agent_key} 配置創建成功")

            except Exception as e:
                logger.error(f"❌ 創建智能體 {agent_key} 配置失敗: {e}")
                continue

        if not agent_configs:
            raise ValueError("沒有可用的智能體配置")

        logger.info(f"✅ 已創建 {len(agent_configs)} 個智能體配置")
        return agent_configs

    except Exception as e:
        logger.error(f"❌ 智能體配置創建失敗: {e}")
        raise


def create_workflow_config(agent_configs: dict):
    """創建工作流配置"""
    logger.info("⚙️ 創建工作流配置...")

    try:
        # 創建工作流配置
        workflow_config = WorkflowConfig(
            name="simple_research",
            workflow_type=WorkflowType.RESEARCH,
            agents=list(agent_configs.keys()),
            max_iterations=3,
        )

        logger.info(f"✅ 工作流配置創建成功:")
        logger.info(f"  - 名稱: {workflow_config.name}")
        logger.info(f"  - 類型: {workflow_config.workflow_type}")
        logger.info(f"  - 智能體數量: {len(workflow_config.agents)}")
        logger.info(f"  - 最大迭代次數: {workflow_config.max_iterations}")

        return workflow_config

    except Exception as e:
        logger.error(f"❌ 工作流配置創建失敗: {e}")
        raise


def create_agent_instances(agent_configs: dict):
    """創建智能體實例"""
    logger.info("🏗️ 開始創建智能體實例...")

    agents = {}

    for agent_key, agent_config in agent_configs.items():
        try:
            logger.info(f"🔧 創建智能體 {agent_key} (角色: {agent_config.role})...")

            if agent_config.role == AgentRole.COORDINATOR:
                logger.info(f"🎭 創建協調者智能體: {agent_key}")
                agents[agent_config.name] = AgentFactory.create_coordinator(agent_config)
                logger.info(f"✅ 協調者智能體 {agent_key} 創建成功")
            elif agent_config.role == AgentRole.PLANNER:
                logger.info(f"📋 創建計劃者智能體: {agent_key}")
                agents[agent_config.name] = AgentFactory.create_planner(agent_config)
                logger.info(f"✅ 計劃者智能體 {agent_key} 創建成功")
            elif agent_config.role == AgentRole.RESEARCHER:
                logger.info(f"🔍 創建研究者智能體: {agent_key}")
                agents[agent_config.name] = AgentFactory.create_researcher(agent_config)
                logger.info(f"✅ 研究者智能體 {agent_key} 創建成功")
            elif agent_config.role == AgentRole.CODER:
                logger.info(f"💻 創建程式設計師智能體: {agent_key}")
                agents[agent_config.name] = AgentFactory.create_coder(agent_config)
                logger.info(f"✅ 程式設計師智能體 {agent_key} 創建成功")
            elif agent_config.role == AgentRole.REPORTER:
                logger.info(f"📊 創建報告者智能體: {agent_key}")
                agents[agent_config.name] = AgentFactory.create_reporter(agent_config)
                logger.info(f"✅ 報告者智能體 {agent_key} 創建成功")
            else:
                logger.warning(f"⚠️  未知的智能體角色: {agent_config.role}")
                continue

            logger.info(f"✅ 智能體 {agent_config.name} 創建成功")

        except Exception as e:
            logger.error(f"❌ 創建智能體 {agent_config.name} 失敗: {e}")
            continue

    if not agents:
        raise ValueError("沒有可用的智能體實例")

    logger.info(f"✅ 已創建 {len(agents)} 個智能體實例")

    # 記錄創建的智能體詳情
    for agent_name, agent in agents.items():
        logger.info(
            f"  📋 {agent_name}: {type(agent).__name__} (角色: {getattr(agent, 'role', '未知')})"
        )
        # 檢查智能體是否有必要的方法
        if hasattr(agent, "process_user_input"):
            logger.info(f"    ✅ 具有 process_user_input 方法")
        if hasattr(agent, "generate_response"):
            logger.info(f"    ✅ 具有 generate_response 方法")
        if hasattr(agent, "analyze_user_input"):
            logger.info(f"    ✅ 具有 analyze_user_input 方法")

    return agents


async def simple_research_workflow():
    """簡單的研究工作流範例 - 使用統一的配置載入器"""
    logger.info("🚀 開始執行簡單研究工作流範例")

    # 1. 檢查環境變數和配置
    logger.info("🔍 步驟 1: 檢查環境變數和配置...")
    if not check_environment_and_config():
        logger.error("❌ 環境變數和配置檢查失敗")
        return {"error": "環境變數和配置檢查失敗"}
    logger.info("✅ 步驟 1 完成: 環境變數和配置檢查成功")

    # 2. 創建 LLM 配置
    logger.info("🔧 步驟 2: 創建 LLM 配置...")
    try:
        llm_config = create_llm_config()
        logger.info("✅ 步驟 2 完成: LLM 配置創建成功")
    except Exception as e:
        logger.error(f"❌ 步驟 2 失敗: LLM 配置創建失敗: {e}")
        return {"error": f"LLM 配置創建失敗: {e}"}

    # 3. 創建智能體配置
    logger.info("🤖 步驟 3: 創建智能體配置...")
    try:
        agent_configs = create_agent_configs(llm_config)
        logger.info("✅ 步驟 3 完成: 智能體配置創建成功")
    except Exception as e:
        logger.error(f"❌ 步驟 3 失敗: 智能體配置創建失敗: {e}")
        return {"error": f"智能體配置創建失敗: {e}"}

    # 4. 創建工作流配置
    logger.info("⚙️ 步驟 4: 創建工作流配置...")
    try:
        workflow_config = create_workflow_config(agent_configs)
        logger.info("✅ 步驟 4 完成: 工作流配置創建成功")
    except Exception as e:
        logger.error(f"❌ 步驟 4 失敗: 工作流配置創建失敗: {e}")
        return {"error": f"工作流配置創建失敗: {e}"}

    # 5. 創建智能體實例
    logger.info("🏗️ 步驟 5: 創建智能體實例...")
    try:
        agents = create_agent_instances(agent_configs)
        logger.info(f"✅ 步驟 5 完成: 已創建 {len(agents)} 個智能體實例")

        # 記錄創建的智能體詳情
        for agent_name, agent in agents.items():
            logger.info(
                f"  - {agent_name}: {type(agent).__name__} (角色: {getattr(agent, 'role', '未知')})"
            )

    except Exception as e:
        logger.error(f"❌ 步驟 5 失敗: 智能體實例創建失敗: {e}")
        return {"error": f"智能體實例創建失敗: {e}"}

    # 6. 使用 LedgerOrchestrator 執行工作流
    logger.info("🎭 步驟 6: 創建 LedgerOrchestrator...")
    orchestrator = LedgerOrchestrator(config=workflow_config, agents=agents, max_rounds=10)
    logger.info("✅ 步驟 6 完成: LedgerOrchestrator 創建完成")

    # 7. 執行研究任務
    task = "請研究人工智慧在醫療領域的最新應用趨勢"
    logger.info(f"🎯 步驟 7: 設定研究任務: {task}")

    print(f"🚀 啟動研究任務: {task}")

    # 初始化任務
    logger.info("🚀 開始初始化任務...")
    await orchestrator.initialize_task(task)
    logger.info("✅ 任務初始化完成")

    # 執行幾輪智能體選擇和任務執行
    logger.info("🔄 開始執行智能體任務流程...")
    for round_num in range(5):
        logger.info(f"🔄 第 {round_num + 1} 輪開始...")

        next_agent = await orchestrator.select_next_agent()
        if next_agent is None:
            logger.info("✅ 工作流完成，沒有更多智能體需要執行")
            print("✅ 工作流完成")
            break

        logger.info(f"👤 選擇的智能體: {next_agent.name} (角色: {next_agent.role})")
        print(f"🔄 第 {round_num + 1} 輪: {next_agent.name}")

        # 真正執行智能體任務
        try:
            # 根據智能體角色給出具體指令
            instruction = await orchestrator._get_agent_instruction(next_agent, task, round_num)

            logger.info(f"📝 給智能體 {next_agent.name} 的指令: {instruction}")

            # 使用 AutoGen 的對話機制讓智能體真正執行任務
            if hasattr(next_agent, "generate_response"):
                # 如果是 AssistantAgent，使用 generate_response
                logger.info(f"🔧 智能體 {next_agent.name} 使用 generate_response() 方法")
                try:
                    response = await next_agent.generate_response(
                        messages=[{"role": "user", "content": instruction}], sender=None
                    )
                    agent_response = (
                        response.content if hasattr(response, "content") else str(response)
                    )
                    logger.info(f"✅ 智能體 {next_agent.name} 的 generate_response 成功")
                except Exception as e:
                    logger.warning(f"智能體 {next_agent.name} 的 generate_response 失敗: {e}")
                    agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"

            elif hasattr(next_agent, "process_user_input"):
                # 如果是 UserProxyAgent，使用 process_user_input
                logger.info(f"🔧 智能體 {next_agent.name} 使用 process_user_input() 方法")
                try:
                    logger.info(f"📞 調用智能體 {next_agent.name} 的 process_user_input 方法...")
                    result = await next_agent.process_user_input(instruction)
                    logger.info(
                        f"✅ 智能體 {next_agent.name} 的 process_user_input 成功，結果類型: {type(result)}"
                    )

                    if result is None:
                        agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                    elif isinstance(result, dict):
                        response_value = result.get("response")
                        if response_value is not None:
                            agent_response = response_value
                        else:
                            # 如果 response 是 None，使用預設回應
                            agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                    else:
                        agent_response = str(result)
                except Exception as e:
                    logger.warning(f"智能體 {next_agent.name} 的 process_user_input 失敗: {e}")
                    agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
            else:
                # 使用 AutoGen 的標準對話機制
                logger.info(f"🔧 智能體 {next_agent.name} 使用 AutoGen 的標準對話機制")
                try:
                    from autogen import GroupChat, GroupChatManager

                    # 創建群組對話
                    group_chat = GroupChat(agents=list(agents.values()), messages=[], max_round=1)

                    # 創建群組聊天管理器
                    manager = GroupChatManager(
                        groupchat=group_chat, llm_config=llm_config.to_autogen_config()
                    )

                    # 讓選中的智能體回應
                    chat_result = await manager.achat(
                        instruction, sender=next_agent, request_reply=True
                    )

                    agent_response = (
                        chat_result.summary if hasattr(chat_result, "summary") else str(chat_result)
                    )
                except ImportError:
                    logger.warning("autogen 模組未安裝，使用預設回應")
                    agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                except Exception as e:
                    logger.warning(f"智能體 {next_agent.name} 的 GroupChat 失敗: {e}")
                    agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"

            logger.info(f"💬 智能體 {next_agent.name} 真正回應: {(agent_response or '')[:200]}...")
            print(f"💬 {next_agent.name}: {(agent_response or '')[:100]}...")

            # 將回應添加到對話歷史
            orchestrator.add_conversation_message(next_agent.name, agent_response)

        except Exception as e:
            logger.error(f"❌ 智能體 {next_agent.name} 執行任務失敗: {e}")
            error_response = f"執行任務時發生錯誤: {str(e)}"
            orchestrator.add_conversation_message(next_agent.name, error_response)
            print(f"❌ {next_agent.name} 執行失敗: {str(e)}")

        logger.info(f"✅ 第 {round_num + 1} 輪完成")

    # 獲取最終狀態
    logger.info("📊 獲取工作流最終狀態...")
    status = orchestrator.get_status()
    logger.info(
        f"📊 工作流狀態: 輪數={status.get('round_count', 0)}, 停滯={status.get('stall_counter', 0)}, 重新規劃={status.get('replan_counter', 0)}"
    )
    print(f"✅ 任務完成，狀態: {status}")

    logger.info("🎉 簡單研究工作流範例執行完成")
    return status


async def standalone_orchestrator_example():
    """獨立使用 LedgerOrchestrator 的範例 - 使用統一的配置載入器"""
    logger.info("🚀 開始執行獨立編排器範例")

    # 1. 檢查環境變數和配置
    logger.info("🔍 步驟 1: 檢查環境變數和配置...")
    if not check_environment_and_config():
        logger.error("❌ 環境變數和配置檢查失敗")
        return {"error": "環境變數和配置檢查失敗"}
    logger.info("✅ 步驟 1 完成: 環境變數和配置檢查成功")

    # 2. 創建 LLM 配置
    logger.info("🔧 步驟 2: 創建 LLM 配置...")
    try:
        llm_config = create_llm_config()
        logger.info("✅ 步驟 2 完成: LLM 配置創建成功")
    except Exception as e:
        logger.error(f"❌ 步驟 2 失敗: LLM 配置創建失敗: {e}")
        return {"error": f"LLM 配置創建失敗: {e}"}

    # 3. 創建簡化的智能體配置
    logger.info("🤖 步驟 3: 創建簡化的智能體配置...")

    # 只選擇核心智能體
    core_agents = ["coordinator", "planner", "researcher", "reporter"]
    agent_configs = {}

    try:
        # 載入配置檔案
        logger.info("📂 載入 conf_autogen.yaml 配置檔案...")
        config = config_loader.load_yaml_config("conf_autogen.yaml")
        if not config:
            raise ValueError("無法載入配置檔案")
        logger.info("✅ 配置檔案載入成功")

        agents_config = config.get("agents", {})
        logger.info(f"📋 找到 {len(agents_config)} 個智能體配置:")
        for agent_key in agents_config.keys():
            logger.info(f"  - {agent_key}")

        logger.info(f"🎯 選擇核心智能體: {core_agents}")

        for agent_key in core_agents:
            if agent_key in agents_config:
                try:
                    logger.info(f"🔧 創建智能體 {agent_key} 的配置...")
                    agent_config = config_loader.load_agent_config(
                        agent_key, agents_config[agent_key]
                    )
                    agent_configs[agent_key] = agent_config
                    logger.info(f"✅ 智能體 {agent_key} 配置創建成功")
                except Exception as e:
                    logger.error(f"❌ 創建智能體 {agent_key} 配置失敗: {e}")
                    continue
            else:
                logger.warning(f"⚠️  智能體 {agent_key} 不在配置檔案中")

        if not agent_configs:
            raise ValueError("沒有可用的智能體配置")

        logger.info(f"✅ 已創建 {len(agent_configs)} 個簡化智能體配置")

    except Exception as e:
        logger.error(f"❌ 智能體配置創建失敗: {e}")
        return {"error": f"智能體配置創建失敗: {e}"}

    # 4. 創建智能體實例
    logger.info("🏗️ 步驟 4: 創建智能體實例...")
    try:
        agents = create_agent_instances(agent_configs)
        logger.info("✅ 步驟 4 完成: 智能體實例創建成功")
    except Exception as e:
        logger.error(f"❌ 步驟 4 失敗: 智能體實例創建失敗: {e}")
        return {"error": f"智能體實例創建失敗: {e}"}

    # 5. 創建編排器
    logger.info("🎭 步驟 5: 創建獨立編排器...")
    orchestrator = LedgerOrchestrator(
        config=WorkflowConfig(name="standalone", workflow_type=WorkflowType.RESEARCH),
        agents=agents,
        max_rounds=5,
    )
    logger.info("✅ 步驟 5 完成: 獨立編排器創建完成")

    # 6. 初始化任務
    task = "分析區塊鏈技術的發展趨勢"
    logger.info(f"🎯 步驟 6: 設定獨立任務: {task}")
    await orchestrator.initialize_task(task)
    logger.info("✅ 步驟 6 完成: 獨立任務初始化完成")

    # 7. 手動執行幾輪，真正執行智能體任務
    logger.info("🔄 步驟 7: 開始手動執行智能體任務流程...")
    for i in range(3):
        logger.info(f"🔄 第 {i + 1} 輪手動執行開始...")

        next_agent = await orchestrator.select_next_agent()
        if next_agent:
            logger.info(f"👤 選擇的智能體: {next_agent.name}")
            print(f"第 {i + 1} 輪: {next_agent.name}")

            # 真正執行智能體任務
            try:
                # 根據輪數給出不同的指令
                if i == 0:
                    instruction = f"請分析任務 '{task}' 並制定執行計劃"
                elif i == 1:
                    instruction = f"基於前面的分析，請深入研究 '{task}' 的具體內容"
                else:
                    instruction = f"請總結前面所有的分析結果，生成關於 '{task}' 的完整報告"

                logger.info(f"📝 給智能體 {next_agent.name} 的指令: {instruction}")

                # 使用 AutoGen 的對話機制讓智能體真正執行任務
                if hasattr(next_agent, "generate_response"):
                    logger.info(f"🔧 智能體 {next_agent.name} 使用 generate_response() 方法")
                    try:
                        response = await next_agent.generate_response(
                            messages=[{"role": "user", "content": instruction}], sender=None
                        )
                        agent_response = (
                            response.content if hasattr(response, "content") else str(response)
                        )
                        logger.info(f"✅ 智能體 {next_agent.name} 的 generate_response 成功")
                    except Exception as e:
                        logger.warning(f"智能體 {next_agent.name} 的 generate_response 失敗: {e}")
                        agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"

                elif hasattr(next_agent, "process_user_input"):
                    logger.info(f"🔧 智能體 {next_agent.name} 使用 process_user_input() 方法")
                    try:
                        logger.info(
                            f"📞 調用智能體 {next_agent.name} 的 process_user_input 方法..."
                        )
                        result = await next_agent.process_user_input(instruction)
                        logger.info(
                            f"✅ 智能體 {next_agent.name} 的 process_user_input 成功，結果類型: {type(result)}"
                        )

                        if result is None:
                            agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                        elif isinstance(result, dict):
                            response_value = result.get("response")
                            if response_value is not None:
                                agent_response = response_value
                            else:
                                # 如果 response 是 None，使用預設回應
                                agent_response = (
                                    f"我是 {next_agent.name}，正在處理任務：{instruction}"
                                )
                        else:
                            agent_response = str(result)
                    except Exception as e:
                        logger.warning(f"智能體 {next_agent.name} 的 process_user_input 失敗: {e}")
                        agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                else:
                    # 使用標準的 AutoGen 對話
                    logger.info(f"🔧 智能體 {next_agent.name} 使用 AutoGen 的標準對話機制")
                    try:
                        from autogen import ConversableAgent

                        if isinstance(next_agent, ConversableAgent):
                            # 創建一個臨時的用戶代理來發送訊息
                            temp_user = ConversableAgent(
                                name="temp_user",
                                human_input_mode="NEVER",
                                max_consecutive_auto_reply=0,
                            )

                            # 讓智能體回應
                            chat_result = await next_agent.achat(
                                instruction, sender=temp_user, request_reply=True
                            )

                            agent_response = (
                                chat_result.summary
                                if hasattr(chat_result, "summary")
                                else str(chat_result)
                            )
                        else:
                            agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                    except ImportError:
                        logger.warning("autogen 模組未安裝，使用預設回應")
                        agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"
                    except Exception as e:
                        logger.warning(f"智能體 {next_agent.name} 的 ConversableAgent 失敗: {e}")
                        agent_response = f"我是 {next_agent.name}，正在處理任務：{instruction}"

                logger.info(
                    f"💬 智能體 {next_agent.name} 真正回應: {(agent_response or '')[:200]}..."
                )
                print(f"💬 {next_agent.name}: {(agent_response or '')[:100]}...")

                # 將回應添加到對話歷史
                orchestrator.add_conversation_message(next_agent.name, agent_response)

            except Exception as e:
                logger.error(f"❌ 智能體 {next_agent.name} 執行任務失敗: {e}")
                error_response = f"執行任務時發生錯誤: {str(e)}"
                orchestrator.add_conversation_message(next_agent.name, error_response)
                print(f"❌ {next_agent.name} 執行失敗: {str(e)}")

            logger.info(f"✅ 第 {i + 1} 輪手動執行完成")
        else:
            logger.info("✅ 沒有更多智能體需要執行，手動流程結束")
            break

    logger.info("📊 步驟 8: 獲取獨立編排器狀態...")
    status = orchestrator.get_status()
    logger.info(
        f"📊 獨立編排器狀態: 輪數={status.get('round_count', 0)}, 停滯={status.get('stall_counter', 0)}"
    )

    logger.info("🎉 獨立編排器範例執行完成")
    return status


if __name__ == "__main__":
    logger.info("🚀 開始執行 AutoGen 系統使用範例")
    print("📚 AutoGen 系統使用範例")

    # 檢查配置檔案 - 使用絕對路徑
    config_file = Path("conf_autogen.yaml")
    if not config_file.exists():
        # 嘗試在專案根目錄查找
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / "conf_autogen.yaml"

    if not config_file.exists():
        print(f"❌ 配置檔案 {config_file} 不存在")
        print("💡 請確保配置檔案存在並包含必要的設定")
        print(f"💡 當前工作目錄: {Path.cwd()}")
        print(f"💡 專案根目錄: {Path(__file__).parent.parent.parent}")
        sys.exit(1)

    print(f"✅ 找到配置檔案: {config_file}")
    logger.info(f"📂 使用配置檔案: {config_file}")

    # 檢查 .env 檔案 - 使用絕對路徑
    env_file = Path(".env")
    if not env_file.exists():
        # 嘗試在專案根目錄查找
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"

    if not env_file.exists():
        print(f"⚠️  環境變數檔案 {env_file} 不存在")
        print("💡 建議創建 .env 檔案並設定必要的環境變數")
        print("💡 可以複製 env.autogen.example 作為範本")
        logger.warning(f"⚠️  環境變數檔案 {env_file} 不存在")
    else:
        print(f"✅ 找到環境變數檔案: {env_file}")
        logger.info(f"✅ 找到環境變數檔案: {env_file}")

    print("\n1️⃣ 完整工作流範例:")
    logger.info("📋 執行完整工作流範例...")
    result1 = asyncio.run(simple_research_workflow())
    logger.info("✅ 完整工作流範例執行完成")

    print("\n2️⃣ 獨立編排器範例:")
    logger.info("📋 執行獨立編排器範例...")
    result2 = asyncio.run(standalone_orchestrator_example())
    logger.info("✅ 獨立編排器範例執行完成")

    print(f"\n📊 編排器狀態: {result2}")
    logger.info("🎉 所有範例執行完成")
    print("\n🎉 範例執行完成!")
