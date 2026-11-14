"""Reproduce per-call measurements using the provided billing simulator."""
from question1.agent import SupportCopilot
from question2.agent import SupportPipeline

PUBLIC = ("T-1001", "T-1002", "T-1003", "T-1004")


def main() -> None:
    for agent_class in (SupportCopilot, SupportPipeline):
        print(f"\n{agent_class.__name__}")
        for ticket_id in PUBLIC:
            agent = agent_class()
            result = agent.handle_ticket(ticket_id)
            for call in agent.session.calls:
                print(f"{ticket_id} {call.label}: input={call.input_tokens}, "
                      f"cached={call.cached_prefix_tokens}, output={call.output_tokens}, "
                      f"points={call.points()}; {result.action} / {result.kb_article}")


if __name__ == "__main__":
    main()
