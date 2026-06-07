import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker
from maa.toolkit import Toolkit

import story_actions


def main():
    project_root = AGENT_DIR.parent
    Toolkit.init_option(str(project_root))
    Tasker.set_log_dir(str(project_root / "debug"))

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        sys.exit(1)

    socket_id = sys.argv[-1]
    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
