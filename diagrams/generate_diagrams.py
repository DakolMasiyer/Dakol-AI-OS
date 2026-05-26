import graphviz
import os

os.makedirs("/home/user/Dakol-AI-OS/diagrams/output", exist_ok=True)

COLORS = {
    "user":    "#4A90D9",
    "router":  "#2C3E50",
    "claude":  "#E74C3C",
    "gpt":     "#F39C12",
    "local":   "#8E44AD",
    "agent":   "#F39C12",
    "fusion":  "#7B68EE",
    "memory":  "#2ECC71",
    "output":  "#1ABC9C",
    "winner":  "#27AE60",
    "low":     "#BDC3C7",
}

def base_graph(name, direction="TD"):
    g = graphviz.Digraph(name, format="png")
    g.attr(rankdir=direction, bgcolor="white", fontname="Helvetica", pad="0.5")
    g.attr("node", fontname="Helvetica", fontsize="11", style="filled", margin="0.2,0.1")
    g.attr("edge", fontname="Helvetica", fontsize="10")
    return g


# ─────────────────────────────────────────────
# 1. CORE ARCHITECTURE
# ─────────────────────────────────────────────
def diagram_core():
    g = base_graph("core_architecture", "TB")
    g.attr(label="Dakol-AI-OS  —  Core Architecture", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("user",   "User Task",                          shape="oval",      fillcolor=COLORS["user"],   fontcolor="white")
    g.node("router", "scripts/router.py\nroute_task()",    shape="box",       fillcolor=COLORS["router"], fontcolor="white")
    g.node("analyze","analyze_task()\nskills/router_skills.py", shape="diamond", fillcolor="#ECF0F1", fontcolor="black")

    g.node("claude", "Claude API\nclaude-3-5-sonnet",      shape="box",       fillcolor=COLORS["claude"], fontcolor="white")
    g.node("gpt",    "OpenAI GPT\ngpt-4o-mini",            shape="box",       fillcolor=COLORS["gpt"],    fontcolor="white")
    g.node("local",  "Local Ollama\ncoder-pro:latest",     shape="box",       fillcolor=COLORS["local"],  fontcolor="white")

    g.node("output", "Model Output",                       shape="box",       fillcolor=COLORS["output"], fontcolor="white")

    g.node("orch",   "Orchestrator\nagents/orchestrator.py", shape="box",     fillcolor=COLORS["router"], fontcolor="white")
    g.node("sync",   "SyncAgent\ndomain_weight x1.3",     shape="box",       fillcolor=COLORS["agent"],  fontcolor="white")
    g.node("audio",  "AudioAgent\ndomain_weight x1.0",    shape="box",       fillcolor=COLORS["agent"],  fontcolor="white")
    g.node("code",   "CodeAgent\ndomain_weight x1.0",     shape="box",       fillcolor=COLORS["agent"],  fontcolor="white")

    g.node("fusion", "Fusion Brain\nOllama LLM",           shape="box",       fillcolor=COLORS["fusion"], fontcolor="white")
    g.node("fo",     "final_intent\nbest_agent\nconfidence", shape="box",     fillcolor=COLORS["fusion"], fontcolor="white")

    g.node("log",    "memory/log.py\nlog_event()",         shape="box",       fillcolor=COLORS["memory"], fontcolor="white")
    g.node("mem",    "memory/logs.json",                   shape="cylinder",  fillcolor=COLORS["memory"], fontcolor="white")

    g.edge("user",   "router")
    g.edge("router", "analyze")
    g.edge("analyze","claude", label="design / architecture\n/ pipeline / licensing")
    g.edge("analyze","gpt",    label="code / api / fastapi\n/ build / implement")
    g.edge("analyze","local",  label="everything else")
    g.edge("claude", "output")
    g.edge("gpt",    "output")
    g.edge("local",  "output")
    g.edge("router", "orch")
    g.edge("orch",   "sync")
    g.edge("orch",   "audio")
    g.edge("orch",   "code")
    g.edge("sync",   "fusion")
    g.edge("audio",  "fusion")
    g.edge("code",   "fusion")
    g.edge("fusion", "fo")
    g.edge("output", "log")
    g.edge("fo",     "log")
    g.edge("log",    "mem")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/1_core_architecture", cleanup=True)
    print("1. Core architecture done")


# ─────────────────────────────────────────────
# 2. SYNCMASTER AGENT
# ─────────────────────────────────────────────
def diagram_sync():
    g = base_graph("syncmaster", "TB")
    g.attr(label="SyncMaster Agent  —  How It Works", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("task",  'User Task\ne.g. "Tag this track BPM and key"', shape="oval",    fillcolor=COLORS["user"],   fontcolor="white")
    g.node("agent", "SyncAgent\nanalyze_task()",                    shape="box",     fillcolor=COLORS["agent"],  fontcolor="white")
    g.node("k1",    "Contains\ntag / bpm / metadata\ntempo / key?", shape="diamond", fillcolor="#ECF0F1",        fontcolor="black")
    g.node("k2",    "Contains\nmusic / audio / sound\ntrack / song?",shape="diamond",fillcolor="#ECF0F1",        fontcolor="black")

    g.node("i1",    "intent: metadata_analysis\nraw confidence: 0.9", shape="box",  fillcolor=COLORS["winner"], fontcolor="white")
    g.node("i2",    "intent: audio_understanding\nraw confidence: 0.8",shape="box", fillcolor=COLORS["gpt"],    fontcolor="white")
    g.node("i3",    "intent: general_analysis\nraw confidence: 0.6",  shape="box",  fillcolor=COLORS["low"],    fontcolor="black")

    g.node("boost", "Apply domain_weight x 1.3",                    shape="box",     fillcolor=COLORS["router"], fontcolor="white")
    g.node("score", "Boosted Scores\n0.9 x 1.3 = 1.17\n0.8 x 1.3 = 1.04\n0.6 x 1.3 = 0.78", shape="box", fillcolor=COLORS["router"], fontcolor="white")
    g.node("orch",  "Orchestrator\ncompares all agent scores",       shape="box",     fillcolor=COLORS["router"], fontcolor="white")
    g.node("win",   "SyncAgent wins\nHighest confidence score",      shape="box",     fillcolor=COLORS["winner"], fontcolor="white")
    g.node("fuse",  "Fusion Brain declares\nbest_agent: sync_agent\nfinal_intent: metadata_analysis", shape="box", fillcolor=COLORS["fusion"], fontcolor="white")

    g.edge("task",  "agent")
    g.edge("agent", "k1")
    g.edge("k1",    "i1",    label="Yes")
    g.edge("k1",    "k2",    label="No")
    g.edge("k2",    "i2",    label="Yes")
    g.edge("k2",    "i3",    label="No")
    g.edge("i1",    "boost")
    g.edge("i2",    "boost")
    g.edge("i3",    "boost")
    g.edge("boost", "score")
    g.edge("score", "orch")
    g.edge("orch",  "win")
    g.edge("win",   "fuse")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/2_syncmaster_agent", cleanup=True)
    print("2. SyncMaster agent done")


# ─────────────────────────────────────────────
# 3. TECH DOMAIN
# ─────────────────────────────────────────────
def diagram_tech():
    g = base_graph("tech_domain", "TB")
    g.attr(label="Tech Domain  —  Build an API Endpoint", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("task",  "Engineer:\nBuild a REST API\nfor user authentication",  shape="oval", fillcolor=COLORS["user"],   fontcolor="white")
    g.node("router","Router detects:\napi / build / implement",              shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("gpt",   "OpenAI GPT\nCode generation",                           shape="box",  fillcolor=COLORS["gpt"],    fontcolor="white")
    g.node("out",   "Returns FastAPI\nauthentication endpoint code",         shape="box",  fillcolor=COLORS["output"], fontcolor="white")
    g.node("orch",  "Orchestrator",                                          shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("ca",    "CodeAgent\nconfidence: 0.9  HIGH",                      shape="box",  fillcolor=COLORS["winner"], fontcolor="white")
    g.node("sa",    "SyncAgent\nconfidence: 0.6  low",                       shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("aa",    "AudioAgent\nconfidence: 0.5  low",                      shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("fuse",  "Fusion Brain\nbest_agent: code_agent\nfinal_intent: code_execution", shape="box", fillcolor=COLORS["fusion"], fontcolor="white")
    g.node("log",   "Memory Log\ntask + code output\n+ agent decision",      shape="cylinder", fillcolor=COLORS["memory"], fontcolor="white")

    g.edge("task",  "router")
    g.edge("router","gpt",  label="Routes to")
    g.edge("gpt",   "out")
    g.edge("task",  "orch")
    g.edge("orch",  "ca")
    g.edge("orch",  "sa")
    g.edge("orch",  "aa")
    g.edge("ca",    "fuse")
    g.edge("sa",    "fuse")
    g.edge("aa",    "fuse")
    g.edge("out",   "log")
    g.edge("fuse",  "log")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/3_tech_domain", cleanup=True)
    print("3. Tech domain done")


# ─────────────────────────────────────────────
# 4. FILM DOMAIN
# ─────────────────────────────────────────────
def diagram_film():
    g = base_graph("film_domain", "TB")
    g.attr(label="Film Domain  —  Score Licensing Pipeline", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("task",  "Film Producer:\nDesign a licensing pipeline\nfor film score distribution", shape="oval", fillcolor=COLORS["user"],   fontcolor="white")
    g.node("router","Router detects:\ndesign / licensing / pipeline",                          shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("claude","Claude API\nArchitecture + deep reasoning",                               shape="box",  fillcolor=COLORS["claude"], fontcolor="white")
    g.node("out",   "Returns full pipeline\ndesign and licensing strategy",                    shape="box",  fillcolor=COLORS["output"], fontcolor="white")
    g.node("orch",  "Orchestrator",                                                            shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("fa",    "FilmAgent\ndetects: score / license / distribute\nconfidence: 0.9  HIGH", shape="box",  fillcolor=COLORS["winner"], fontcolor="white")
    g.node("aa",    "AudioAgent\nconfidence: 0.7",                                             shape="box",  fillcolor=COLORS["gpt"],    fontcolor="white")
    g.node("ca",    "CodeAgent\nconfidence: 0.5  low",                                         shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("fuse",  "Fusion Brain\nbest_agent: film_agent\nfinal_intent: licensing_pipeline",  shape="box",  fillcolor=COLORS["fusion"], fontcolor="white")
    g.node("log",   "Memory Log\nBuilds history of every\nlicensing decision",                 shape="cylinder", fillcolor=COLORS["memory"], fontcolor="white")

    g.edge("task",  "router")
    g.edge("router","claude", label="Routes to")
    g.edge("claude","out")
    g.edge("task",  "orch")
    g.edge("orch",  "fa")
    g.edge("orch",  "aa")
    g.edge("orch",  "ca")
    g.edge("fa",    "fuse")
    g.edge("aa",    "fuse")
    g.edge("ca",    "fuse")
    g.edge("out",   "log")
    g.edge("fuse",  "log")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/4_film_domain", cleanup=True)
    print("4. Film domain done")


# ─────────────────────────────────────────────
# 5. MEDIA DOMAIN
# ─────────────────────────────────────────────
def diagram_media():
    g = base_graph("media_domain", "TB")
    g.attr(label="Media Domain  —  Content Strategy", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("task",  "Media Editor:\nAnalyse audience data\nand suggest content strategy",        shape="oval", fillcolor=COLORS["user"],   fontcolor="white")
    g.node("router","Router detects:\ndesign / architecture / pipeline",                          shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("claude","Claude API\nAnalysis + strategy reasoning",                                  shape="box",  fillcolor=COLORS["claude"], fontcolor="white")
    g.node("out",   "Returns content\nstrategy recommendations",                                  shape="box",  fillcolor=COLORS["output"], fontcolor="white")
    g.node("orch",  "Orchestrator",                                                               shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("ma",    "MediaAgent\ndetects: content / audience\n/ publish / broadcast\nconfidence: 0.9  HIGH", shape="box", fillcolor=COLORS["winner"], fontcolor="white")
    g.node("ca",    "CodeAgent\nconfidence: 0.5  low",                                            shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("sa",    "SyncAgent\nconfidence: 0.5  low",                                            shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("fuse",  "Fusion Brain\nbest_agent: media_agent\nfinal_intent: content_strategy",      shape="box",  fillcolor=COLORS["fusion"], fontcolor="white")
    g.node("log",   "Memory Log\nBuilds history of media\ndecisions over time",                   shape="cylinder", fillcolor=COLORS["memory"], fontcolor="white")

    g.edge("task",  "router")
    g.edge("router","claude", label="Routes to")
    g.edge("claude","out")
    g.edge("task",  "orch")
    g.edge("orch",  "ma")
    g.edge("orch",  "ca")
    g.edge("orch",  "sa")
    g.edge("ma",    "fuse")
    g.edge("ca",    "fuse")
    g.edge("sa",    "fuse")
    g.edge("out",   "log")
    g.edge("fuse",  "log")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/5_media_domain", cleanup=True)
    print("5. Media domain done")


# ─────────────────────────────────────────────
# 6. DEFENSE DOMAIN
# ─────────────────────────────────────────────
def diagram_defense():
    g = base_graph("defense_domain", "TB")
    g.attr(label="Defense Domain  —  Threat Detection Pipeline", labelloc="t", fontsize="16", fontname="Helvetica-Bold")

    g.node("task",  "Defense Analyst:\nDesign a threat detection pipeline\nfor cyber intrusion signals", shape="oval", fillcolor=COLORS["user"],   fontcolor="white")
    g.node("router","Router detects:\ndesign / pipeline / architecture",                               shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("claude","Claude API\nComplex reasoning + threat modeling",                                 shape="box",  fillcolor=COLORS["claude"], fontcolor="white")
    g.node("out",   "Returns threat detection\narchitecture + response plan",                          shape="box",  fillcolor=COLORS["output"], fontcolor="white")
    g.node("orch",  "Orchestrator",                                                                    shape="box",  fillcolor=COLORS["router"], fontcolor="white")
    g.node("da",    "DefenseAgent\ndetects: threat / intrusion\n/ intel / surveillance\nconfidence: 0.95  HIGH", shape="box", fillcolor=COLORS["winner"], fontcolor="white")
    g.node("ca",    "CodeAgent\nconfidence: 0.6",                                                      shape="box",  fillcolor=COLORS["gpt"],    fontcolor="white")
    g.node("sa",    "SyncAgent\nconfidence: 0.5  low",                                                 shape="box",  fillcolor=COLORS["low"],    fontcolor="black")
    g.node("fuse",  "Fusion Brain\nbest_agent: defense_agent\nfinal_intent: threat_detection",         shape="box",  fillcolor=COLORS["fusion"], fontcolor="white")
    g.node("log",   "Memory Log\nAudit trail of all\nthreat assessments",                              shape="cylinder", fillcolor=COLORS["memory"], fontcolor="white")

    g.edge("task",  "router")
    g.edge("router","claude", label="Routes to")
    g.edge("claude","out")
    g.edge("task",  "orch")
    g.edge("orch",  "da")
    g.edge("orch",  "ca")
    g.edge("orch",  "sa")
    g.edge("da",    "fuse")
    g.edge("ca",    "fuse")
    g.edge("sa",    "fuse")
    g.edge("out",   "log")
    g.edge("fuse",  "log")

    g.render("/home/user/Dakol-AI-OS/diagrams/output/6_defense_domain", cleanup=True)
    print("6. Defense domain done")


if __name__ == "__main__":
    diagram_core()
    diagram_sync()
    diagram_tech()
    diagram_film()
    diagram_media()
    diagram_defense()
    print("\nAll diagrams saved to diagrams/output/")
