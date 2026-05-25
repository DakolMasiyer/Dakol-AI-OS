def route_task(task: str):
    model = analyze_task(task)

    print("\nSelected model:", model)

    # ----------------------------
    # EXECUTE MODEL LAYER
    # ----------------------------
    if model == "claude":
        output = run_claude(task)

    elif model == "codex":
        output = run_codex(task)

    else:
        output = run_local(task)

    # ----------------------------
    # MULTI-AGENT FUSION LAYER
    # ----------------------------
    orchestrator = Orchestrator()
    agent_result = orchestrator.route(task)

    fusion = agent_result.get("fusion_output", {})

    print("\n--- AGENT FUSION OUTPUT ---")
    print("Final Intent:", fusion.get("final_intent"))
    print("Reasoning:", fusion.get("reasoning"))
    print("Best Agent:", fusion.get("best_agent"))
    print("Confidence:", fusion.get("confidence"))

    # ----------------------------
    # MEMORY LOGGING (SAFE + CONSISTENT)
    # ----------------------------
    entry = log_event(
        task,
        model,
        output,
        agent_result
    )

    print("\n--- MEMORY CONFIRMATION ---")
    print("Logged task:", entry["task"])
    print("Model used:", entry["model_used"])
    print("Saved at:", entry["timestamp"])

    return output