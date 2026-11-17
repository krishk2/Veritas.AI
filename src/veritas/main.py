import sys
from veritas.core.graph import create_graph
from veritas.core.observability import get_observability_callbacks

def main():
    print("=" * 60)
    print("  Veritas.AI - Multi-Agent Verification Pipeline")
    print("=" * 60)
    
    app = create_graph()
    
    claim = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Drinking bleach cures COVID-19."
    print(f"\n[Claim to Verify]: '{claim}'\n")
    
    initial_state = {"claim": claim}
    
    config = {}
    callbacks = get_observability_callbacks()
    if callbacks:
        config["callbacks"] = callbacks
    
    print("Running pipeline agents...")
    try:
        final_state = {}
        for output in app.stream(initial_state, config=config if config else None):
            for agent_name, state_update in output.items():
                print(f"  [OK] Finished agent: {agent_name}")
                if isinstance(state_update, dict):
                    final_state.update(state_update)
                    
        print("\n" + "=" * 60)
        print("  VERIFICATION RESULT")
        print("=" * 60)
        print(f"  Verdict:     {final_state.get('verdict', 'UNKNOWN')}")
        confidence = final_state.get('adjusted_confidence', final_state.get('confidence', 0.0))
        print(f"  Confidence:  {confidence:.2f}")
        print(f"  Explanation: {final_state.get('explanation', 'N/A')}")
        
        evidence = final_state.get('evidence', [])
        if evidence:
            print(f"\n  Evidence ({len(evidence)} items):")
            for item in evidence:
                print(f"    - [{item.get('label')}] {item.get('sentence')} (score: {item.get('score')})")
                
        credibility = final_state.get('credibility_report', [])
        if credibility:
            print(f"\n  Source Credibility ({len(credibility)} sources):")
            for src in credibility:
                print(f"    - [{src.get('status')}] {src.get('domain')}")
                
        print("=" * 60)
        
    except Exception as e:
        print(f"\nGraph execution failed: {e}")
            
    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
