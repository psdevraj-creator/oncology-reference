"""
Specialized DeepSeek Flash prompts — extract structure from text for dmc/Plotly rendering.
Each prompt gives clinical examples of text → structured JSON conversion.
CRITICAL: Extract EXACT text verbatim. Never invent numbers. Use null when data absent.
"""

PROMPTS: dict[str, dict] = {

    "molecular_pathogenesis": {
        "prompt": """Extract genes, pathways, drugs and their connections from this oncology text for a network diagram.
Examples: text "BRCA1 mutations impair DNA repair" → node {id:"BRCA1",type:"gene"}, node {id:"DNA repair",type:"pathway"}, edge {source:"BRCA1",target:"DNA repair",type:"inhibits"}
text "PIK3CA activates PI3K, targeted by alpelisib" → node {id:"PIK3CA",type:"gene"}, node {id:"PI3K",type:"pathway"}, node {id:"alpelisib",type:"drug"}, edges source-target
text "HER2 amplification drives RTK signaling, targeted by trastuzumab" → nodes and edges
text "CDK4/6 regulates cell cycle, targeted by palbociclib" → nodes and edges
text "ESR1 mutations drive endocrine resistance" → nodes
text "NTRK fusions targeted by larotrectinib" → nodes+edges
text "FGFR amplifications" → node, no drug unless stated
CRITICAL: Every gene, pathway, drug mentioned must be a node. Every stated relationship must be an edge.
Types: node types = gene/pathway/targetable/drug. Edge types = activates/inhibits/targets.
Split text into labeled sections preserving original text verbatim.

Return ONLY: {"sections":[{"heading":"SHORT","content":"VERBATIM"}],"network":{"nodes":[{"id":"NAME","type":"gene|pathway|targetable|drug"}],"edges":[{"source":"ID","target":"ID","type":"activates|inhibits|targets"}]}}""",
        "max_tokens": 16384,
    },

    "staging": {
        "prompt": """Extract TNM staging categories and stage groups with exact size/description from text.
Examples: text "T1 ≤20mm" → {"category":"T1","description":"Tumor ≤20 mm"}
text "N0: no regional lymph node metastasis" → {"category":"N0","description":"No regional lymph node metastasis"}
text "M0: no distant metastasis" → {"category":"M0","description":"No distant metastasis"}
text "Stage IA: T1 N0 M0" → {"stage":"IA","t":"T1","n":"N0","m":"M0"}
text "5-year OS 99%" → {"stages":["I"],"os":[99]}
text "5-year OS 85% for stage II" → {"stages":["II"],"os":[85]}
Split into sections preserving original text verbatim.
If survival % is stated anywhere in the text, extract it per stage.

Return ONLY: {"sections":[{"heading":"TNM","content":"VERBATIM"}],"t_stages":[...],"n_stages":[...],"m_stages":[...],"stage_groups":[...],"chart":{"stages":["I","II","III","IV"],"os":[99,85,55,28]}}""",
        "max_tokens": 8192,
    },

    "complications": {
        "prompt": """Extract complications as structured cards from clinical text. Do NOT invent incidence numbers unless explicitly stated.
Examples: text "Lymphedema: educate patients, monitor, refer for management" → {"name":"Lymphedema","detail":"VERBATIM","severity":"moderate"}
text "Neutropenia occurs in 40% of patients" → {"name":"Neutropenia","detail":"VERBATIM","incidence":"40%","severity":"severe"}
text "Cardiotoxicity is a risk with trastuzumab" → {"name":"Cardiotoxicity","detail":"VERBATIM","severity":"severe"}
If incidence % is explicitly stated, extract it. Otherwise set incidence to null. NEVER invent.
Split details from management. If data has disease_related and treatment_related keys, process each.

Return ONLY: {"sections":[{"heading":"Complications","content":"VERBATIM"}],"cards":[{"name":"Name","detail":"VERBATIM","incidence":"NN% or null","severity":"mild|moderate|severe"}],"chart":{"labels":[...],"values":[...],"severities":[...]}}""",
        "max_tokens": 8192,
    },

    "prognosis": {
        "prompt": """Extract survival data and prognostic factors as structured data.
Examples: text "5-year OS: stage I 99%, stage II 85%, stage III 55%, stage IV 28%" → chart data
text "ER-positive tumors have favorable prognosis" → {"factor":"ER positivity","impact":"Favorable","detail":"VERBATIM"}
text "TNBC has aggressive course with high early recurrence" → {"factor":"TNBC","impact":"Unfavorable","detail":"VERBATIM"}
text "pCR after neoadjuvant therapy predicts improved DFS and OS" → {"factor":"pCR","impact":"Favorable","detail":"VERBATIM"}
text "RCB is prognostic within subtypes [275]" → {"factor":"RCB","impact":"Favorable","detail":"VERBATIM"}

Split the original text verbatim into sections. Extract EXACT survival % only if stated.
Mark factor impacts as Favorable/Unfavorable/Variable.

Return ONLY: {"sections":[{"heading":"Prognosis","content":"VERBATIM"}],"chart":{"stages":["I","II","III","IV"],"os":[99,85,55,28]},"factors":[{"factor":"Name","impact":"Favorable|Unfavorable","detail":"VERBATIM"}]}""",
        "max_tokens": 8192,
    },

    "surveillance": {
        "prompt": """Restructure surveillance/follow-up into timeline items. Extract time intervals verbatim.
Examples: text "Year 1-2: every 3-4 months, clinical exam + mammogram" → {"title":"Year 1-2: Every 3-4 months","body":"Clinical exam, mammogram","icon":"bi-calendar-check"}
text "Year 3-5: every 6 months" → {"title":"Year 3-5: Every 6 months","body":"Clinical exam","icon":"bi-calendar2-check"}
text "Annual mammogram after 5 years" → {"title":"Year 5+: Annual","body":"Mammogram, clinical exam","icon":"bi-calendar3"}

Return ONLY: {"sections":[{"heading":"Surveillance","content":"VERBATIM"}],"timeline":[{"title":"Time period","body":"Actions","icon":"bi-calendar-check"}]}""",
        "max_tokens": 4096,
    },

    "follow_up": {
        "prompt": """Restructure follow-up plan into timeline and late effects. Extract intervals and effects verbatim.
Examples: text "Annual mammogram year 1-5" → timeline item
text "Cardiotoxicity screening due to anthracycline exposure" → {"name":"Cardiotoxicity","detail":"VERBATIM"}
text "Lymphedema surveillance" → {"name":"Lymphedema","detail":"VERBATIM"}

Return ONLY: {"sections":[{"heading":"Follow-Up","content":"VERBATIM"}],"timeline":[{"title":"Period","body":"Actions","icon":"bi-calendar2-check"}],"late_effects":[{"name":"Effect","detail":"VERBATIM"}]}""",
        "max_tokens": 4096,
    },

    "clinical_features": {
        "prompt": """Extract symptoms with frequency percentages and alarm/red flag indicators.
Examples: text "Breast lump present in 70% of cases" → {"name":"Breast lump","frequency":"70%","alarm":false,"detail":"VERBATIM"}
text "Peau d'orange (inflammatory breast cancer) in 10%" → {"name":"Peau d'orange","frequency":"10%","alarm":true,"detail":"VERBATIM"}
text "Pain is a common presenting symptom" → {"name":"Pain","frequency":"common","alarm":false,"detail":"VERBATIM"}
text "Nipple discharge (bloody) is a red flag" → {"name":"Bloody nipple discharge","frequency":null,"alarm":true,"detail":"VERBATIM"}
Extract EXACT frequency % if stated. Mark alarm=true for red flags/warning signs.

Return ONLY: {"sections":[{"heading":"Symptoms","content":"VERBATIM"}],"symptoms":[{"name":"S","detail":"VERBATIM","frequency":"NN% or text","alarm":false}],"alarms":[{"name":"Red Flag","detail":"VERBATIM"}],"chart":{"labels":["S"],"values":[70]}}""",
        "max_tokens": 4096,
    },

    "risk_factors": {
        "prompt": """Structure risk factors with attributable risk. Extract factor, type, strength, detail. NEVER invent numbers.
Examples: text "BRCA1 mutation, genetic, OR 11-45, 5-10% of all breast cancers, tested for any age [BINV-Q 2]" → {"factor":"BRCA1 mutation","type":"Genetic","strength":"High","detail":"VERBATIM"}
text "Alcohol consumption, lifestyle, RR 1.1 per 10g/day" → {"factor":"Alcohol","type":"Lifestyle","strength":"Moderate","detail":"VERBATIM"}
text "Obesity in postmenopausal women, demographic/lifestyle" → {"factor":"Obesity (postmenopausal)","type":"Lifestyle","strength":"Moderate","detail":"VERBATIM"}
text "Family history" → {"factor":"Family history","type":"Genetic","strength":"High","detail":"VERBATIM"}
Strength = High/Moderate/Low based on OR/RR stated or clinical context.
Split into sections by risk type, preserving text verbatim.

Return ONLY: {"sections":[{"heading":"Genetic","content":"VERBATIM"}],"cards":[{"factor":"Name","type":"Genetic|Lifestyle|Environmental|Demographic|Medical|Hormonal","strength":"High|Moderate|Low","detail":"VERBATIM"}],"waterfall":{"labels":[...],"values":[...],"types":[...]}}""",
        "max_tokens": 4096,
    },

    "management_principles": {
        "prompt": """Convert management principles into structured decision cards and flowchart data.
Split by intent (curative/palliative/adjuvant). Extract decision nodes from text.
Examples: text "PS 0-1 patients receive curative intent chemotherapy" → decision node PS 0-1, treatment node chemotherapy
text "Patients with metastatic disease receive palliative systemic therapy" → decision node, treatment node
text "MDT review is mandatory before treatment" → {"card":{"title":"MDT","detail":"VERBATIM"}}

Return ONLY: {"sections":[{"heading":"Overview","content":"VERBATIM"}],"flowchart":{"nodes":[{"id":"n1","label":"Decision","type":"decision|treatment|outcome"}],"edges":[{"source":"n1","target":"n2","label":"criteria"}]},"cards":[{"title":"Intent","detail":"VERBATIM","color":"#10b981|#f59e0b|#6366f1"}]}""",
        "max_tokens": 8192,
    },

    "management_pathways": {
        "prompt": """Convert treatment decision pathways into Cytoscape flowchart nodes and edges from the structured pathway data.
The input is a list of pathway objects with pathway_id, title, branching_basis, nodes (each node has criteria, options, adjuvant_logic).
For each pathway, create decision nodes (criteria) and treatment nodes (options/recommendations), connected by edges with labels.
Example: pathway with criteria "ER+/HER2-" → decision node, "Endocrine therapy + CDK4/6 inhibitor" → treatment node, edge with label "Yes"
If adjuvant_logic states "if node-positive" → additional decision node branching from treatment node.

Return ONLY: {"sections":[{"heading":"Pathway Title","content":"VERBATIM"}],"flowcharts":[{"title":"Name","nodes":[{"id":"unique_id","label":"Criteria/Options text","type":"decision|treatment"}],"edges":[{"source":"from_id","target":"to_id","label":"Decision label"}]}]}""",
        "max_tokens": 8192,
    },

    "surgery": {
        "prompt": """Structure surgery details into procedure decision cards. Split role from procedures from principles.
Examples: text "Wide local excision for T1-T2 tumors, contraindicated in multicentric disease" → {"name":"Wide local excision","condition":"T1-T2 tumors","contraindications":"Multicentric disease","detail":"VERBATIM"}
text "Mastectomy indicated for T3-T4, multicentric disease, or patient preference" → {"name":"Mastectomy","condition":"T3-T4 / multicentric","detail":"VERBATIM"}
text "Sentinel node biopsy is standard for clinically node-negative axilla" → {"name":"SLNB","condition":"cN0","detail":"VERBATIM"}

Return ONLY: {"sections":[{"heading":"Surgery","content":"VERBATIM"}],"cards":[{"name":"Procedure","condition":"When applicable","contraindications":"When not","detail":"VERBATIM"}]}""",
        "max_tokens": 4096,
    },

    "radiation_therapy": {
        "prompt": """Extract RT dose details including total dose (Gy), fractions, treatment sites, timing.
Examples: text "50 Gy in 25 fractions over 5 weeks to the whole breast" → {"label":"Whole breast","total_dose":50,"fractions":25,"body":"50 Gy / 25 fractions / 5 weeks"}
text "Boost of 10-16 Gy in 5-8 fractions to tumor bed" → {"label":"Tumor bed boost","total_dose":14,"fractions":7,"body":"10-16 Gy / 5-8 fractions"}
text "Accelerated partial breast irradiation: 38.5 Gy in 10 fractions BID" → {"label":"APBI","total_dose":38.5,"fractions":10,"body":"38.5 Gy / 10 fractions BID"}

Return ONLY: {"sections":[{"heading":"RT","content":"VERBATIM"}],"gauges":[{"label":"Tot Dose","total_dose":NN,"fractions":NN,"unit":"Gy"}],"timeline":[{"title":"Regimen","body":"Dose / fractions / timing","icon":"bi-lightning-charge"}]}""",
        "max_tokens": 4096,
    },

    "systemic_therapy": {
        "prompt": """Structure systemic therapy into treatment line cards and timeline. Extract drug names, combinations, and settings.
Examples: text "1st line: AC-T (doxorubicin + cyclophosphamide x4 → paclitaxel x12) for adjuvant" → {"name":"AC-T","line":"1st","setting":"Adjuvant","drugs":"Doxorubicin,Cyclophosphamide,Paclitaxel","detail":"VERBATIM"}
text "Pertuzumab + trastuzumab + docetaxel for HER2+ metastatic" → {"name":"THP","line":"1st","setting":"Metastatic","drugs":"Pertuzumab,Trastuzumab,Docetaxel","detail":"VERBATIM"}
text "T-DM1 for residual disease post-neoadjuvant" → {"name":"T-DM1","setting":"Post-neoadjuvant","drugs":"T-DM1","detail":"VERBATIM"}

Return ONLY: {"sections":[{"heading":"Systemic","content":"VERBATIM"}],"cards":[{"name":"Regimen","setting":"Setting","drugs":"Drug1,Drug2","detail":"VERBATIM"}],"timeline":[{"title":"Line","body":"Regimens","icon":"bi-1-circle-fill|bi-2-circle-fill|bi-3-circle-fill"}]}""",
        "max_tokens": 4096,
    },

    "clinical_pearls": {
        "prompt": """Categorize clinical pearls by topic. Preserve text verbatim. Categories: Diagnosis, Staging, Treatment, Prognosis, Complications, Supportive Care, Follow-up, Pearls.
Example: text "Always check ER/PR/HER2 before starting systemic therapy" → {"text":"VERBATIM","category":"Treatment"}
text "LCIS is a risk factor, not a malignancy" → {"text":"VERBATIM","category":"Diagnosis"}
text "5-year OS for stage I is >95%" → {"text":"VERBATIM","category":"Prognosis"}

Return ONLY: {"sections":[{"heading":"Pearls","content":"VERBATIM"}],"cards":[{"text":"VERBATIM","category":"Diagnosis|Staging|Treatment|Prognosis|Complications|Pearls"}]}""",
        "max_tokens": 2048,
    },
}
