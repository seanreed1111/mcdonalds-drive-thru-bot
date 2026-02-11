"""Render all blog diagrams as PNGs using mermaid-py."""

from mermaid import Mermaid
from mermaid.graph import Graph

OUTPUT_DIR = "c:/Users/sqr99/NewPythonProjects/VoiceAI/mcdonalds-drive-thru-bot/docs/blogs/images"

diagrams = {
    "01-system-overview": """\
graph TB
    subgraph User["User"]
        CLI["CLI Chat Interface"]
    end

    subgraph Orchestrator["orchestrator package"]
        Main["main.py<br/>Chat Loop"]
        GraphMod["graph.py<br/>LangGraph Graph"]
        Tools["tools.py<br/>4 Tools"]
        Config["config.py<br/>Settings"]
        Models["models.py<br/>Pydantic Models"]
    end

    subgraph External["External Services"]
        Mistral["Mistral AI<br/>LLM"]
        LF["Langfuse v3<br/>Tracing + Prompts"]
    end

    subgraph Data["Data"]
        MenuJSON["breakfast-v2.json<br/>21 Items"]
    end

    CLI <--> Main
    Main --> GraphMod
    GraphMod --> Tools
    GraphMod <--> Mistral
    GraphMod <-.-> LF
    Main --> Config
    Tools --> Models
    MenuJSON --> Main

    style User fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style Orchestrator fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style External fill:#fce7f3,stroke:#ec4899,stroke-width:2px
    style Data fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style GraphMod fill:#10b981,color:#ffffff,stroke:#059669,stroke-width:2px
""",
    "02-langgraph-flow": """\
graph LR
    START(("START")) --> O

    O["orchestrator<br/>─────────────<br/>Invoke LLM with<br/>menu + order context"]

    O -->|"tool_calls"| T["tools<br/>─────────────<br/>Execute tool calls<br/>lookup, add, get, finalize"]
    O -->|"no tool_calls"| END(("END"))

    T --> U["update_order<br/>─────────────<br/>Apply add_item results<br/>to current_order"]

    U -->|"finalize called"| END
    U -->|"continue"| O

    style START fill:#10b981,color:#ffffff,stroke:#059669,stroke-width:3px
    style END fill:#ef4444,color:#ffffff,stroke:#dc2626,stroke-width:3px
    style O fill:#3b82f6,color:#ffffff,stroke:#2563eb,stroke-width:2px
    style T fill:#f59e0b,color:#ffffff,stroke:#d97706,stroke-width:2px
    style U fill:#a855f7,color:#ffffff,stroke:#7c3aed,stroke-width:2px
""",
    "03-tool-architecture": """\
graph TB
    subgraph pure["Tool Layer - Pure Functions"]
        L["lookup_menu_item<br/>───────────<br/>Search menu by name<br/>Return match or suggestions"]
        A["add_item_to_order<br/>───────────<br/>Validate item + modifiers<br/>Return result dict"]
        G["get_current_order<br/>───────────<br/>Return order summary"]
        F["finalize_order<br/>───────────<br/>Mark order complete"]
    end

    subgraph bridge["State Bridge"]
        U["update_order node<br/>───────────<br/>Parse ToolMessages<br/>Construct Items<br/>Merge into Order"]
    end

    L -->|"must call first"| A
    A -->|"result dict"| U
    G -->|"read-only"| RET["Return to LLM"]
    F -->|"triggers END"| RET

    style pure fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style bridge fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style L fill:#3b82f6,color:#ffffff,stroke:#2563eb,stroke-width:2px
    style A fill:#10b981,color:#ffffff,stroke:#059669,stroke-width:2px
    style G fill:#f59e0b,color:#ffffff,stroke:#d97706,stroke-width:2px
    style F fill:#ef4444,color:#ffffff,stroke:#dc2626,stroke-width:2px
    style U fill:#d97706,color:#ffffff,stroke:#92400e,stroke-width:2px
""",
    "04-prompt-compilation": """\
sequenceDiagram
    participant ON as orchestrator_node
    participant LF as Langfuse
    participant LLM as Mistral AI

    ON->>LF: get_prompt("drive-thru/orchestrator", label="production")
    alt Langfuse available
        LF-->>ON: Template with placeholders
    else Langfuse unavailable
        ON->>ON: Use FALLBACK_SYSTEM_PROMPT
    end

    ON->>ON: Compile: replace location, menu, order
    ON->>LLM: SystemMessage + conversation messages
    LLM-->>ON: Response with tool_calls or text
""",
    "05-state-schema": """\
classDiagram
    class MessagesState {
        LangGraph Built-in
        list messages
    }

    class DriveThruState {
        Graph State
        Menu menu
        Order current_order
        list reasoning
    }

    class Menu {
        str menu_id
        str menu_name
        str menu_version
        Location location
        list items
        from_json_file() Menu
    }

    class Order {
        str order_id
        list items
        __add__(Item) Order
    }

    class Item {
        str item_id
        str name
        CategoryName category_name
        Size default_size
        Size size
        int quantity
        list modifiers
        list available_modifiers
        __add__(Item) Item
        __eq__() bool
    }

    class Modifier {
        str modifier_id
        str name
    }

    MessagesState <|-- DriveThruState
    DriveThruState --> Menu
    DriveThruState --> Order
    Menu "1" --> "*" Item : contains
    Order "1" --> "*" Item : items
    Item "*" --> "*" Modifier : modifiers
""",
    "06-v0-vs-v1": """\
graph TB
    subgraph v0["v0 Design - Explicit State Machine (Rejected)"]
        G0["Greeting"] --> IC["Intent<br/>Classifier"]
        IC --> ML["Menu<br/>Lookup"]
        IC --> OC["Order<br/>Confirm"]
        IC --> MO["Modify<br/>Order"]
        ML --> IC2["Re-classify"]
        OC --> FIN["Finalize"]
        MO --> IC2
        IC2 --> ML
        IC2 --> OC
    end

    subgraph v1["v1 Design - LLM Orchestrator (Chosen)"]
        O1["orchestrator"] -->|"tool_calls"| T1["tools"]
        O1 -->|"respond"| E1(("END"))
        T1 --> U1["update_order"]
        U1 --> O1
    end

    style v0 fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style v1 fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style O1 fill:#3b82f6,color:#ffffff,stroke:#2563eb,stroke-width:2px
    style T1 fill:#f59e0b,color:#ffffff,stroke:#d97706,stroke-width:2px
    style U1 fill:#a855f7,color:#ffffff,stroke:#7c3aed,stroke-width:2px
""",
    "07-dual-compilation": """\
graph TB
    Builder["_builder<br/>StateGraph with nodes + edges<br/>───────────<br/>Defined once in graph.py"]

    Builder -->|"compile()"| Studio["graph.py: graph<br/>───────────<br/>No checkpointer<br/>Used by LangGraph Studio"]

    Builder -->|"compile(checkpointer=MemorySaver())"| CLIGraph["main.py: graph<br/>───────────<br/>With MemorySaver<br/>Used by CLI chat loop"]

    style Builder fill:#3b82f6,color:#ffffff,stroke:#2563eb,stroke-width:2px
    style Studio fill:#f59e0b,color:#ffffff,stroke:#d97706,stroke-width:2px
    style CLIGraph fill:#10b981,color:#ffffff,stroke:#059669,stroke-width:2px
""",
}

for name, source in diagrams.items():
    g = Graph(name, source)
    m = Mermaid(g)
    path = f"{OUTPUT_DIR}/{name}.png"
    m.to_png(path)
    print(f"Rendered: {path}")

print("All diagrams rendered.")
