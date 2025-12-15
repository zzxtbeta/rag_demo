# Agent 程序设计：统一 Program 抽象

## 1. 核心设计思想

### 1.1 关键洞察

**StatefulProgram 的 Python 逻辑（业务状态变更）可以重新执行**，因为它们很快。
**真正耗时的是 Plan 执行（LLM 调用、工具调用等）**。

因此：
- **只需要 checkpoint Plan 调用的结果**
- **Replay = 重新执行 Python 逻辑，遇到已完成的 Plan 调用时直接返回缓存结果**
- **不需要复杂的 StateField 机制来同步业务状态**

### 1.2 两层 ID 设计

**核心思想**：`program_id` 标识整个 Program，`execution_id` 标识每次 Plan 执行。

```
┌─────────────────────────────────────────────────────────────────┐
│  program_id = "game-001"                                        │
│  (Program 级别，管理 Plan 调用历史和 Agent 计数器)                │
├─────────────────────────────────────────────────────────────────┤
│  StatefulProgram                                                │
│  ├── program_id: "game-001"                                     │
│  ├── _counters: {"alice": 2, "bob": 1, "_": 0}                  │
│  └── _results: {                                                │
│        "game-001:alice:0": ExecutionResult {...},               │
│        "game-001:alice:1": ExecutionResult {...},               │
│        "game-001:bob:0": ExecutionResult {...},                 │
│      }                                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
              每次 Plan 调用生成新的 execution_id
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  execution_id = "game-001:alice:0"                              │
│  (Plan 执行级别，底层 ExecutionContext 按此隔离)                  │
├─────────────────────────────────────────────────────────────────┤
│  ExecutionContext (现有的，完全不变)                              │
│  ├── execution_id: "game-001:alice:0"                           │
│  ├── inputs: {...}                                              │
│  ├── node_outputs: {...}                                        │
│  ├── completed_nodes: {...}                                     │
│  └── loop_states: {...}                                         │
└─────────────────────────────────────────────────────────────────┘
```

**ID 规则**：
- **StatelessProgram (IRPlan)**：`program_id == execution_id`，只执行一次
- **StatefulProgram**：
  - 有 Agent：`execution_id = f"{program_id}:{agent_id}:{counter}"`
  - 无 Agent：`execution_id = f"{program_id}::{counter}"`

### 1.3 统一 Program 抽象

```
┌─────────────────────────────────────────────────────────────────┐
│                       Program（统一抽象）                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌───────────────────────────┐ │
│  │  StatelessProgram           │  │    StatefulProgram        │ │
│  │  (无状态)                   │  │    (有状态)               │ │
│  │                             │  │                           │ │
│  │  - PhysicalPlan (IR 编译)   │  │  - 绑定 Runtime           │ │
│  │  - program_id == exec_id    │  │  - 内部调用多个 Plan      │ │
│  │  - 每次调用独立             │  │  - submit 自动注入 Agent  │ │
│  │  - 无缓存                   │  │  - 结果缓存，支持 replay  │ │
│  └─────────────────────────────┘  └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 设计

### 2.1 Agent 定位

**Agent = 身份 + 能力描述 + 本地状态**

```
┌─────────────────────────────────────────────────────────────────┐
│                           Agent                                  │
├─────────────────────────────────────────────────────────────────┤
│  身份 (Identity)                                                 │
│  ├── agent_id: "alice"                                          │
│  └── name: "Alice"                                              │
├─────────────────────────────────────────────────────────────────┤
│  能力/角色描述 (Profile)                                         │
│  ├── role: "werewolf"                                           │
│  ├── skills: ["reasoning", "persuasion"]                        │
│  └── system_prompt: "你是一个狼人..."                            │
├─────────────────────────────────────────────────────────────────┤
│  本地状态 (Local State) - 执行期间动态变化                        │
│  ├── memory: {"观察": [...], "怀疑": [...]}                     │
│  └── conversation: [{"role": "user", "content": "..."}]         │
└─────────────────────────────────────────────────────────────────┘
```

**设计原则**：
- Agent 是**纯数据实体**，不绑定 Runtime/Program
- Agent 可以**动态创建**、复制、序列化
- Agent 的本地状态由 Program 管理

### 2.2 Agent 实现

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import copy

@dataclass
class Agent:
    """
    Agent：身份 + 能力描述 + 本地状态。
    
    设计原则：
    - 纯数据实体，不绑定任何执行环境
    - 可以动态创建、复制、序列化
    - 本地状态在执行期间由 Program 管理
    """
    
    # ========== 身份（不可变）==========
    agent_id: str
    name: str = ""
    
    # ========== 能力/角色描述（通常不变）==========
    profile: Dict[str, Any] = field(default_factory=dict)
    # 常用字段：
    #   role: str           - 角色类型
    #   skills: List[str]   - 技能列表
    #   system_prompt: str  - 系统提示词
    #   persona: str        - 人设描述
    
    # ========== 本地状态（执行期间动态变化）==========
    memory: Dict[str, Any] = field(default_factory=dict)
    conversation: List[Dict[str, str]] = field(default_factory=list)
    
    # ========== 属性访问 ==========
    
    @property
    def system_prompt(self) -> str:
        """获取系统提示词"""
        return self.profile.get("system_prompt", "")
    
    @property
    def role(self) -> str:
        """获取角色"""
        return self.profile.get("role", "")
    
    # ========== 本地记忆操作 ==========
    
    def remember(self, key: str, value: Any):
        """存储到本地记忆"""
        self.memory[key] = value
    
    def recall(self, key: str, default=None) -> Any:
        """从本地记忆读取"""
        return self.memory.get(key, default)
    
    def append_memory(self, key: str, value: Any):
        """追加到列表类型的记忆"""
        if key not in self.memory:
            self.memory[key] = []
        self.memory[key].append(value)
    
    # ========== 对话历史操作 ==========
    
    def add_message(self, role: str, content: str):
        """添加对话消息"""
        self.conversation.append({"role": role, "content": content})
    
    def get_messages(self, last_n: int = None) -> List[Dict[str, str]]:
        """获取对话历史"""
        if last_n:
            return self.conversation[-last_n:]
        return self.conversation.copy()
    
    # ========== 状态管理 ==========
    
    def clear_state(self):
        """清空本地状态（保留身份和 profile）"""
        self.memory.clear()
        self.conversation.clear()
    
    def clone(self, new_id: str = None) -> "Agent":
        """克隆 Agent（用于并行执行等场景）"""
        return Agent(
            agent_id=new_id or f"{self.agent_id}-clone",
            name=self.name,
            profile=copy.deepcopy(self.profile),
            memory=copy.deepcopy(self.memory),
            conversation=copy.deepcopy(self.conversation),
        )
    
    # ========== 序列化 ==========
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "profile": self.profile,
            "memory": self.memory,
            "conversation": self.conversation,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        """从字典反序列化"""
        return cls(
            agent_id=data["agent_id"],
            name=data.get("name", ""),
            profile=data.get("profile", {}),
            memory=data.get("memory", {}),
            conversation=data.get("conversation", []),
        )
    
    # ========== 便捷构造器 ==========
    
    @classmethod
    def create(
        cls,
        agent_id: str,
        name: str = None,
        role: str = None,
        system_prompt: str = None,
        **profile_kwargs,
    ) -> "Agent":
        """便捷创建方法"""
        profile = profile_kwargs
        if role:
            profile["role"] = role
        if system_prompt:
            profile["system_prompt"] = system_prompt
        return cls(
            agent_id=agent_id,
            name=name or agent_id,
            profile=profile,
        )
```

### 2.3 Agent vs Program vs Runtime

| 概念 | 职责 | 是否动态创建 |
|------|------|-------------|
| **Agent** | 身份 + 能力 + 本地状态 | ✅ 可以随时创建 |
| **Program** | 执行逻辑 + execution_id 管理 + 缓存 | ✅ 每次任务创建 |
| **Runtime** | 执行环境 + 资源管理 | ❌ 通常全局单例 |
| **Plan** | 具体工作流（无状态） | ❌ 预编译，可复用 |

```
Runtime (全局)
    │
    └── Program (每个任务)
            │
            ├── Agent 1 (动态创建)
            │     ├── profile
            │     └── local state
            │
            ├── Agent 2 (动态创建)
            │     ├── profile
            │     └── local state
            │
            └── Plans (复用)
                  ├── vote_plan
                  └── discuss_plan
```

---

## 3. StatefulProgram 设计

### 3.1 完全封装的 StatefulProgram

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid
import asyncio

class StatefulProgram(Program, ABC):
    """
    有状态 Program - 完全封装版本。
    
    用户只需要：
    1. 继承此类
    2. 实现 main() 方法
    3. 在 main() 中调用 self.submit() / self.run()
    
    特点：
    - 绑定 Runtime（在 __init__ 中传入）
    - submit/run 自动管理 execution_id
    - Agent 信息自动注入到 inputs
    - 支持 replay（结果缓存）
    """
    
    def __init__(self, runtime: "Runtime", program_id: str = None):
        self.runtime = runtime
        self.program_id = program_id or f"prog-{uuid.uuid4().hex[:8]}"
        self._counters: Dict[str, int] = {}  # agent_id -> counter
        self._results: Dict[str, "ExecutionResult"] = {}  # execution_id -> result
    
    # ========== 内部方法 ==========
    
    def _next_execution_id(self, agent: Agent = None) -> str:
        """
        生成 execution_id。
        
        格式：
        - 有 agent: "{program_id}:{agent_id}:{counter}"
        - 无 agent: "{program_id}::{counter}"
        """
        key = agent.agent_id if agent else "_"
        counter = self._counters.get(key, 0)
        self._counters[key] = counter + 1
        
        if agent:
            return f"{self.program_id}:{agent.agent_id}:{counter}"
        else:
            return f"{self.program_id}::{counter}"
    
    def _inject_agent_context(self, inputs: Dict, agent: Agent) -> Dict:
        """
        自动注入 agent 上下文。
        
        Plan 中可以用 $agent.xxx 引用：
        - $agent.id
        - $agent.name
        - $agent.role
        - $agent.system_prompt
        - $agent.profile
        - $agent.profile.xxx
        - $agent.memory
        - $agent.memory.xxx
        - $agent.conversation
        """
        return {
            **inputs,
            "agent": {
                "id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "system_prompt": agent.system_prompt,
                "profile": agent.profile,
                "memory": agent.memory,
                "conversation": agent.get_messages(),
            }
        }
    
    # ========== 用户调用的接口 ==========
    
    async def submit(
        self,
        plan: "Plan",
        inputs: Dict[str, Any] = None,
        agent: Agent = None,
    ) -> "ExecutionResult":
        """
        提交 Plan 执行。
        
        - execution_id 自动生成
        - 支持 replay（缓存命中直接返回）
        - agent 可选，传入时自动注入 agent 信息
        
        Args:
            plan: 要执行的 Plan
            inputs: 输入参数
            agent: 可选，Agent 实例
        
        Returns:
            ExecutionResult
        """
        inputs = inputs or {}
        execution_id = self._next_execution_id(agent)
        
        # 缓存检查（replay 时跳过已完成的调用）
        if execution_id in self._results:
            return self._results[execution_id]
        
        # 注入 agent 信息
        if agent:
            inputs = self._inject_agent_context(inputs, agent)
        
        # 提交执行
        result = await self.runtime.submit(plan, inputs, execution_id=execution_id)
        self._results[execution_id] = result
        return result
    
    async def run(
        self,
        plan: "Plan",
        inputs: Dict[str, Any] = None,
        agent: Agent = None,
    ) -> "ExecutionResult":
        """直接执行（不经调度器）"""
        inputs = inputs or {}
        execution_id = self._next_execution_id(agent)
        
        if execution_id in self._results:
            return self._results[execution_id]
        
        if agent:
            inputs = self._inject_agent_context(inputs, agent)
        
        result = await self.runtime.execute(plan, inputs, execution_id=execution_id)
        self._results[execution_id] = result
        return result
    
    def submit_sync(
        self,
        plan: "Plan",
        inputs: Dict[str, Any] = None,
        agent: Agent = None,
    ) -> "ExecutionResult":
        """同步版本"""
        return asyncio.get_event_loop().run_until_complete(
            self.submit(plan, inputs, agent)
        )
    
    # ========== 用户实现的入口 ==========
    
    @abstractmethod
    async def main(self) -> Any:
        """
        用户实现的主逻辑。
        
        在这里：
        - 定义 Agent（动态创建）
        - 定义或获取 Plan
        - 调用 self.submit(plan, inputs, agent) / self.run(...)
        """
        pass
    
    # ========== 启动方法 ==========
    
    async def start(self) -> Any:
        """启动 Program"""
        return await self.main()
    
    # ========== Checkpoint ==========
    
    def to_checkpoint(self) -> dict:
        """序列化为 checkpoint"""
        return {
            "program_id": self.program_id,
            "counters": self._counters.copy(),
            "results": {
                k: v.to_dict() for k, v in self._results.items()
            },
        }
    
    @classmethod
    def from_checkpoint(cls, runtime: "Runtime", checkpoint: dict) -> "StatefulProgram":
        """从 checkpoint 恢复（需要子类实现）"""
        raise NotImplementedError("Subclass must implement from_checkpoint")
```

### 3.2 Plan 中使用 $agent.xxx 前缀

```python
# 定义 Plan 时，用 $agent.xxx 引用 agent 信息
vote_plan = (
    IRGraphBuilder()
    .add_input("task", "str")
    .add_input("alive_players", "list")
    .add_llm_call("decide", {
        "system_prompt": "$agent.system_prompt",  # 自动注入
        "prompt": """你是 $agent.name（角色：$agent.role）。

你的记忆：$agent.memory

当前存活玩家：$input.alive_players

任务：$input.task

请做出决定。"""
    })
    .add_output("vote", "$nodes.decide.outputs.result")
    .build()
)
```

### 3.3 使用示例

```python
# 之前（繁琐）
result = await runtime.submit(
    vote_plan,
    {
        "task": "投票",
        "alive_players": alive,
        "agent_profile": agent.profile,      # 手动
        "agent_memory": agent.memory,        # 手动
        "conversation": agent.get_messages(), # 手动
    },
)

# 现在（简洁）
result = await self.submit(
    vote_plan,
    {"task": "投票", "alive_players": alive},
    agent=alice,  # agent 信息自动注入
)
```

---

## 4. Runtime.submit 统一接口

Runtime 提供三个统一接口：`submit`（异步）、`execute`（异步）、`submit_sync`（同步）。

```python
class Runtime:
    
    async def submit(
        self,
        program: Program,
        inputs: Dict[str, Any] = None,
        program_id: str = None,
        execution_id: str = None,  # 用于 StatefulProgram 内部调用
    ) -> "ExecutionResult":
        """
        提交 Program 执行（统一接口）。
        
        Args:
            program: 要执行的 Program（StatelessProgram 或 StatefulProgram）
            inputs: 输入参数
            program_id: Program 标识符（StatefulProgram 用）
            execution_id: 执行标识符（内部使用）
        """
        inputs = inputs or {}
        
        if isinstance(program, StatefulProgram):
            # StatefulProgram: 调用 program.start()
            return await program.start()
        elif isinstance(program, StatelessProgram):
            # StatelessProgram: 直接执行
            exec_id = execution_id or program_id or self._generate_execution_id()
            return await self._execute_plan(program, inputs, exec_id)
        else:
            raise TypeError(f"Cannot submit {type(program)}")
    
    async def execute(self, program: Program, inputs: Dict = None, **kwargs):
        """同 submit，立即执行"""
        return await self.submit(program, inputs, **kwargs)
    
    def submit_sync(self, program: Program, inputs: Dict = None, **kwargs):
        """同步版本的 submit"""
        return asyncio.run(self.submit(program, inputs, **kwargs))
    
    async def _execute_plan(
        self, 
        plan: StatelessProgram, 
        inputs: Dict[str, Any], 
        execution_id: str
    ) -> "ExecutionResult":
        """执行 Plan（底层）"""
        exec_ctx = self.executor.create_context(execution_id, inputs)
        return await self.executor.execute(plan, exec_ctx)
    
    def _generate_execution_id(self) -> str:
        return f"exec-{uuid.uuid4().hex[:12]}"
```

---

## 5. Checkpoint 与 Replay

### 5.1 Replay 机制

```
原始执行:
  main() 逻辑 → submit(plan, agent=alice)  → submit(plan, agent=bob)   → ...
                execution_id=prog:alice:0    execution_id=prog:alice:1
                        ↓                            ↓
                  _results 缓存

Replay (从 checkpoint 恢复):
  main() 逻辑 → submit(plan, agent=alice)  → 缓存命中，跳过 LLM
              → submit(plan, agent=bob)    → 缓存命中，跳过 LLM
              → submit(plan, agent=carol)  → 无缓存，重新执行 LLM
              → ...
```

### 5.2 Checkpoint/Restore

```python
# 保存 checkpoint
checkpoint = game.to_checkpoint()
save_to_file("game-001.ckpt", checkpoint)

# 恢复 checkpoint
checkpoint = load_from_file("game-001.ckpt")
# 需要重新创建 Program 实例并恢复状态
game = WerewolfGame(runtime, players, roles)
game._counters = checkpoint["counters"]
game._results = {k: ExecutionResult.from_dict(v) for k, v in checkpoint["results"].items()}

# 继续执行
winner = await game.start()  # replay，已完成的 Plan 调用会跳过
```

---

## 6. 完整示例

### 6.1 狼人杀游戏

```python
from agent_runtime import Runtime
from agent_runtime.program import StatefulProgram, Agent
from agent_runtime.ir import IRGraphBuilder, compile_graph, create_react_graph

class WerewolfGame(StatefulProgram):
    """
    狼人杀游戏。
    
    特点：
    - 普通 Python 代码
    - Agent 动态创建
    - self.submit() 自动注入 Agent 信息
    - Plan 结果自动缓存，支持 replay
    """
    
    def __init__(self, runtime: Runtime, players: list, roles: dict):
        super().__init__(runtime, program_id=f"werewolf-{uuid.uuid4().hex[:8]}")
        self.players = players
        self.roles = roles
        
        # 动态创建 Agents
        self.agents = {
            name: Agent.create(
                agent_id=name.lower(),
                name=name,
                role=role,
                system_prompt=f"你是{name}，身份是{role}。请根据你的身份行动。"
            )
            for name, role in roles.items()
        }
    
    async def main(self) -> str:
        """游戏主逻辑"""
        alive = list(self.players)
        round_num = 0
        
        while not self._is_game_over(alive):
            round_num += 1
            print(f"\n=== 第 {round_num} 轮 ===")
            
            # 夜晚阶段
            victim = await self._run_night(alive)
            if victim:
                alive.remove(victim)
                print(f"  ❌ {victim} 被狼人杀死！")
            
            if self._is_game_over(alive):
                break
            
            # 白天阶段
            eliminated = await self._run_day(alive)
            if eliminated:
                alive.remove(eliminated)
                print(f"  ❌ {eliminated} 被投票出局！")
        
        return self._get_winner(alive)
    
    async def _run_night(self, alive: list) -> str:
        """夜晚阶段：狼人投票"""
        print("\n🌙 夜晚降临...")
        wolves = [p for p in alive if self.roles[p] == "werewolf"]
        
        votes = []
        for wolf in wolves:
            agent = self.agents[wolf]
            
            # 🎯 简洁：只传业务参数，agent 信息自动注入
            result = await self.submit(
                get_vote_plan(),
                {"task": "选择今晚要杀的人", "alive_players": alive},
                agent=agent,
            )
            vote = result.outputs.get("vote")
            votes.append(vote)
            
            # 更新 agent 记忆
            agent.append_memory("night_votes", vote)
        
        if votes:
            return max(set(votes), key=votes.count)
        return None
    
    async def _run_day(self, alive: list) -> str:
        """白天阶段：讨论和投票"""
        print("\n☀️ 天亮了...")
        
        # 讨论
        print("\n--- 讨论阶段 ---")
        for player in alive:
            agent = self.agents[player]
            result = await self.submit(
                get_discuss_plan(),
                {"alive_players": alive},
                agent=agent,
            )
            statement = result.outputs.get("statement", "...")
            print(f"  {player}: {statement[:50]}...")
            agent.add_message("assistant", statement)
        
        # 投票
        print("\n--- 投票阶段 ---")
        votes = {}
        for player in alive:
            agent = self.agents[player]
            result = await self.submit(
                get_vote_plan(),
                {"task": "投票淘汰可疑的人", "alive_players": alive},
                agent=agent,
            )
            vote = result.outputs.get("vote")
            votes[player] = vote
            print(f"  {player} 投给了 {vote}")
            agent.append_memory("day_votes", vote)
        
        # 统计
        vote_counts = {}
        for v in votes.values():
            if v:
                vote_counts[v] = vote_counts.get(v, 0) + 1
        
        if vote_counts:
            return max(vote_counts, key=vote_counts.get)
        return None
    
    def _is_game_over(self, alive: list) -> bool:
        wolves = sum(1 for p in alive if self.roles[p] == "werewolf")
        villagers = len(alive) - wolves
        return wolves == 0 or wolves >= villagers
    
    def _get_winner(self, alive: list) -> str:
        wolves = sum(1 for p in alive if self.roles[p] == "werewolf")
        return "村民" if wolves == 0 else "狼人"


# 预编译的 Plan（全局复用，使用 $agent.xxx）
def get_vote_plan():
    graph = (
        IRGraphBuilder()
        .add_input("task", "str")
        .add_input("alive_players", "list")
        .add_llm_call("decide", {
            "system_prompt": "$agent.system_prompt",
            "prompt": """你是 $agent.name（$agent.role）。

【你的记忆】
$agent.memory

【存活玩家】
$input.alive_players

【任务】
$input.task

请选择一个人。只输出名字。"""
        })
        .add_output("vote", "$nodes.decide.outputs.result")
        .build()
    )
    return compile_graph(graph).plan


def get_discuss_plan():
    graph = (
        IRGraphBuilder()
        .add_input("alive_players", "list")
        .add_llm_call("speak", {
            "system_prompt": "$agent.system_prompt",
            "messages": "$agent.conversation",
            "prompt": """存活玩家：$input.alive_players

请发表你的看法（1-2句话）。"""
        })
        .add_output("statement", "$nodes.speak.outputs.result")
        .build()
    )
    return compile_graph(graph).plan


# 使用示例
async def main():
    runtime = await Runtime.create()
    
    game = WerewolfGame(
        runtime=runtime,
        players=["Alice", "Bob", "Carol", "David", "Eve"],
        roles={
            "Alice": "werewolf",
            "Bob": "werewolf",
            "Carol": "seer",
            "David": "villager",
            "Eve": "villager",
        }
    )
    
    winner = await game.start()
    print(f"\n🏆 游戏结束！{winner}获胜！")
```

### 6.2 多角度问答

```python
class MultiPerspectiveQA(StatefulProgram):
    """
    多角度问答任务：
    1. 用户提问
    2. LLM 生成 k 个回答角度
    3. 每个角度启动一个 ReAct 链路
    4. 汇总结果
    """
    
    def __init__(self, runtime: Runtime, question: str, k: int = 3):
        super().__init__(runtime, program_id=f"multi-qa-{uuid.uuid4().hex[:8]}")
        self.question = question
        self.k = k
    
    async def main(self) -> str:
        """主逻辑"""
        print(f"📝 问题: {self.question}")
        
        # Step 1: 生成 k 个角度
        print(f"\n🔍 生成 {self.k} 个回答角度...")
        result = await self.submit(
            get_perspective_plan(),
            {"question": self.question, "k": self.k}
        )
        perspectives = self._parse_perspectives(result.outputs.get("perspectives", ""))
        print(f"   角度: {perspectives}")
        
        # Step 2: 为每个角度创建 Agent 并执行 ReAct
        answers = []
        for i, perspective in enumerate(perspectives):
            # 动态创建 Agent
            agent = Agent.create(
                agent_id=f"analyst-{i}",
                name=f"角度{i+1}分析师",
                role="analyst",
                perspective=perspective,
                system_prompt=f"你是一个分析师，专注于从「{perspective}」的角度分析问题。"
            )
            agent.remember("perspective", perspective)
            agent.remember("question", self.question)
            
            print(f"\n🤖 Agent [{agent.name}]: {perspective}")
            
            # 执行 ReAct 链路
            result = await self.submit(
                get_react_plan(),
                {"task": f"从「{perspective}」的角度回答问题：{self.question}"},
                agent=agent,
            )
            
            answer = result.outputs.get("answer", "无法回答")
            agent.remember("answer", answer)
            answers.append({
                "perspective": perspective,
                "answer": answer,
            })
            print(f"   回答: {answer[:100]}...")
        
        # Step 3: 汇总结果
        print(f"\n📊 汇总 {len(answers)} 个角度的回答...")
        result = await self.submit(
            get_summarize_plan(),
            {"question": self.question, "answers": json.dumps(answers, ensure_ascii=False)}
        )
        
        final_answer = result.outputs.get("final_answer", "")
        print(f"\n✅ 最终答案:\n{final_answer}")
        
        return final_answer
    
    def _parse_perspectives(self, raw: str) -> list:
        try:
            data = json.loads(raw)
            return data.get("perspectives", [])[:self.k]
        except:
            return [line.strip() for line in raw.split("\n") if line.strip()][:self.k]


# 使用
async def main():
    runtime = await Runtime.create()
    runtime.register_tool("search", lambda query: f"搜索结果: {query}")
    runtime.register_tool("calculate", lambda expr: eval(expr))
    
    qa = MultiPerspectiveQA(
        runtime=runtime,
        question="如何评估一个机器学习模型的性能？",
        k=3,
    )
    
    answer = await qa.start()
```

### 6.3 execution_id 生成示例

```
狼人杀游戏:
werewolf-abc123
    │
    ├── werewolf-abc123:alice:0   (夜晚，Alice 投票)
    ├── werewolf-abc123:bob:0     (夜晚，Bob 投票)
    ├── werewolf-abc123:alice:1   (白天，Alice 发言)
    ├── werewolf-abc123:bob:1     (白天，Bob 发言)
    ├── werewolf-abc123:carol:0   (白天，Carol 发言)
    ├── werewolf-abc123:alice:2   (白天，Alice 投票)
    ├── ...
    └── werewolf-abc123:eve:N     (最后)

多角度问答:
multi-qa-xyz789
    │
    ├── multi-qa-xyz789::0          (生成角度，无 agent)
    ├── multi-qa-xyz789:analyst-0:0 (角度1 ReAct)
    ├── multi-qa-xyz789:analyst-1:0 (角度2 ReAct)
    ├── multi-qa-xyz789:analyst-2:0 (角度3 ReAct)
    └── multi-qa-xyz789::1          (汇总，无 agent)
```

---

## 7. 设计总结

### 7.1 核心要点

| 概念 | 说明 |
|------|------|
| **Agent** | 纯数据实体：身份 + 能力 + 本地状态 |
| **StatefulProgram** | 绑定 Runtime，封装 submit/run，自动注入 Agent |
| **program_id** | Program 实例标识 |
| **execution_id** | Plan 执行标识：`{program_id}:{agent_id}:{counter}` |

### 7.2 Agent 信息自动注入

Plan 中使用 `$agent.xxx` 引用：

| 引用 | 含义 |
|------|------|
| `$agent.id` | agent_id |
| `$agent.name` | 名字 |
| `$agent.role` | 角色 |
| `$agent.system_prompt` | 系统提示词 |
| `$agent.profile` | 完整 profile |
| `$agent.profile.xxx` | profile 中的字段 |
| `$agent.memory` | 本地记忆 |
| `$agent.memory.xxx` | 记忆中的字段 |
| `$agent.conversation` | 对话历史 |

### 7.3 用户编程模型

```python
class MyTask(StatefulProgram):
    
    def __init__(self, runtime: Runtime, ...):
        super().__init__(runtime)
        # 定义任务参数
    
    async def main(self) -> Any:
        # 1. 动态创建 Agents
        agent = Agent.create("worker", role="analyst")
        
        # 2. 调用 Plan（agent 信息自动注入）
        result = await self.submit(some_plan, {"input": "..."}, agent=agent)
        
        # 3. 更新 agent 状态
        agent.remember("result", result.outputs)
        
        # 4. 返回结果
        return result
```

### 7.4 优势

1. **Agent 解耦**：纯数据，动态创建，不绑定 Runtime
2. **完全封装**：submit 自动管理 execution_id 和 Agent 注入
3. **简洁 API**：用户只需实现 `main()`，调用 `self.submit(plan, inputs, agent)`
4. **ID 可追踪**：`prog:alice:3` 清晰显示是哪个 agent 的第几次调用
5. **支持 Replay**：结果缓存，Python 逻辑可重新执行

---

## 8. 与现有实现的对接

### 8.1 需要新增

1. **Agent 类**：纯数据实体
2. **StatefulProgram 基类**：封装 submit/run，管理 counters 和 results
3. **Agent 信息注入**：`_inject_agent_context()` 方法

### 8.2 不需要修改

1. **ExecutionContext**：完全复用，按 execution_id 隔离
2. **PlanExecutor**：完全复用
3. **Runtime.submit**：小幅扩展，支持 execution_id 参数

### 8.3 迁移路径

1. 新增 `Agent` 类
2. 新增 `StatefulProgram` 基类
3. 更新 Plan 解析器支持 `$agent.xxx`
4. 编写示例验证
