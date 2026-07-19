"""
Specialized DeepSeek Flash prompts — one per section. Keeping prompts SHORT and targeted.
CRITICAL: ALL original text preserved verbatim in sections[].content.
"""

PROMPTS: dict[str, dict] = {

    "molecular_pathogenesis": {
        "prompt": """Extract from this oncology text: ALL genes, pathways, drugs, and their connections. Split text into labeled sections verbatim.

Return ONLY: {"sections":[{"heading":"SHORT","content":"VERBATIM"}],"network":{"nodes":[{"id":"NAME","type":"gene|pathway|targetable|drug"}],"edges":[{"source":"ID","target":"ID","type":"activates|inhibits|targets"}]},"summaries":[{"pathway":"N","genes":["G1"],"drugs":"D1,D2","targetable":true}]}""",
        "max_tokens": 16384,
    },

    "staging": {
        "prompt": """Extract TNM staging: T categories (size), N categories, M categories, stage groups with survival %. Preserve all text.

Return ONLY: {"sections":[{"heading":"TNM","content":"VERBATIM"}],"t_stages":[{"category":"T1","description":"s20mm"}],"n_stages":[{"category":"N0","description":"..."}],"m_stages":[{"category":"M0","description":"..."}],"stage_groups":[{"stage":"IA","t":"T1","n":"N0","m":"M0"}],"chart":{"stages":["I","II","III","IV"],"os":[99,85,55,28]}}""",
        "max_tokens": 8192,
    },

    "complications": {
        "prompt": """List all complications with incidence % and severity (mild/moderate/severe). Preserve original text.

Return ONLY: {"sections":[{"heading":"Complications","content":"VERBATIM"}],"chart":{"labels":["Name"],"values":[40],"severities":["severe"]},"cards":[{"name":"Name","incidence":"40%","severity":"severe","detail":"VERBATIM"}]}""",
        "max_tokens": 8192,
    },

    "prognosis": {
        "prompt": """Extract survival by stage (5-yr OS %) and prognostic factors. Preserve text.

Return ONLY: {"sections":[{"heading":"Prognosis","content":"VERBATIM"}],"chart":{"stages":["I","II","III","IV"],"os":[99,85,55,28]},"factors":[{"factor":"Name","impact":"Favorable","detail":"VERBATIM"}]}""",
        "max_tokens": 8192,
    },

    "surveillance": {
        "prompt": """Restructure surveillance schedule into timeline. Preserve all text.

Return ONLY: {"sections":[{"heading":"Surveillance","content":"VERBATIM"}],"timeline":[{"title":"Period","body":"Actions","icon":"bi-calendar-check"}]}""",
        "max_tokens": 4096,
    },

    "follow_up": {
        "prompt": """Restructure follow-up into timeline items and late effects. Preserve all text.

Return ONLY: {"sections":[{"heading":"Follow-Up","content":"VERBATIM"}],"timeline":[{"title":"Period","body":"Actions","icon":"bi-calendar2-check"}],"late_effects":[{"name":"Effect","detail":"VERBATIM"}]}""",
        "max_tokens": 4096,
    },

    "clinical_features": {
        "prompt": """Extract symptoms with frequencies, red flags with alarm indicators. Preserve all text.

Return ONLY: {"sections":[{"heading":"Symptoms","content":"VERBATIM"}],"symptoms":[{"name":"S","detail":"VERBATIM","frequency":"NN%","alarm":false}],"alarms":[{"name":"Red Flag","detail":"VERBATIM"}],"chart":{"labels":["S"],"values":[70]}}""",
        "max_tokens": 4096,
    },

    "risk_factors": {
        "prompt": """Categorize risk factors with attributable risk values. Preserve all text.

Return ONLY: {"sections":[{"heading":"Risk Factors","content":"VERBATIM"}],"waterfall":{"labels":["F"],"values":[45],"types":["Genetic"]},"cards":[{"factor":"Name","type":"Genetic","strength":"High","detail":"VERBATIM"}]}""",
        "max_tokens": 4096,
    },

    "management_principles": {
        "prompt": """Convert management principles into flowchart nodes and intent cards. Preserve all text.

Return ONLY: {"sections":[{"heading":"Overview","content":"VERBATIM"}],"flowchart":{"nodes":[{"id":"n1","label":"Decision","type":"decision|treatment|outcome"}],"edges":[{"source":"n1","target":"n2","label":"criteria"}]},"cards":[{"title":"Intent","detail":"VERBATIM","color":"#10b981"}]}""",
        "max_tokens": 8192,
    },

    "management_pathways": {
        "prompt": """Convert pathways into Cytoscape flowcharts (decision nodes, treatment nodes, edges). Preserve all text.

Return ONLY: {"sections":[{"heading":"Pathway","content":"VERBATIM"}],"flowcharts":[{"title":"Name","nodes":[{"id":"id","label":"Text","type":"decision|treatment"}],"edges":[{"source":"a","target":"b","label":"condition"}]}]}""",
        "max_tokens": 8192,
    },

    "surgery": {
        "prompt": """Structure surgery into procedure cards. Preserve all text.

Return ONLY: {"sections":[{"heading":"Surgery","content":"VERBATIM"}],"cards":[{"name":"Procedure","detail":"VERBATIM"}]}""",
        "max_tokens": 4096,
    },

    "radiation_therapy": {
        "prompt": """Extract RT dose values (Gy), fractions into gauges and timeline. Preserve all text.

Return ONLY: {"sections":[{"heading":"RT","content":"VERBATIM"}],"gauges":[{"label":"Dose","value":50,"unit":"Gy"}],"timeline":[{"title":"Regimen","body":"Details","icon":"bi-lightning-charge"}]}""",
        "max_tokens": 4096,
    },

    "systemic_therapy": {
        "prompt": """Restructure systemic therapy into cards and treatment line timeline. Preserve all text.

Return ONLY: {"sections":[{"heading":"Systemic","content":"VERBATIM"}],"cards":[{"name":"Regimen","drugs":"List","detail":"VERBATIM"}],"timeline":[{"title":"1st Line","body":"Regimens","icon":"bi-1-circle-fill"}]}""",
        "max_tokens": 4096,
    },

    "clinical_pearls": {
        "prompt": """Categorize pearls as Diagnosis/Staging/Treatment/Prognosis. Preserve all text verbatim.

Return ONLY: {"sections":[{"heading":"Pearls","content":"VERBATIM"}],"cards":[{"text":"VERBATIM","category":"Diagnosis"}]}""",
        "max_tokens": 2048,
    },
}
