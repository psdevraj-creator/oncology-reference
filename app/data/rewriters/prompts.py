"""
Specialized DeepSeek Flash prompts — extract structure from text for dmc/Plotly rendering.

ANTI-HALLUCINATION RULES (APPLY TO ALL SECTIONS — NON-NEGOTIABLE):
1. NUMBERS ONLY WHEN SOURCE STATES EXACT VALUE. If source says "generally poor"
   or "3-5 months" without exact %, output null. Never convert metrics.
2. MONTHS ARE NOT PERCENTAGES. "Median OS 3-5 months" means 3-5 MONTHS,
   not 5%. Do not put months values in percentage fields.
3. NULL IS CORRECT. An empty chart is better than a wrong chart.
4. SELF-AUDIT: For every numeric value you output, mentally check:
   "Does the EXACT same number appear verbatim in the source text?"
   If not, remove it and set null.
5. RANGES ARE NOT SINGLE VALUES. "30-78%" range does not equal 30% or 78%
   individually. If source gives a range, the individual stage values are null.
6. CONTEXT MATTERS. A surgical trial stat (94.2% in KLASS-01) is not a
   general population prognosis. Do not apply trial-specific numbers to
   general stage categories.

PENALTY: Outputting invented numbers is CLINICALLY DANGEROUS. A wrong survival
percentage could mislead treatment decisions. Error on the side of null.
"""

PROMPTS: dict[str, dict] = {

    "molecular_pathogenesis": {
        "prompt": """Extract genes, pathways, drugs and their connections from this oncology text for a network diagram.
Examples: text "BRCA1 mutations impair DNA repair" → node {id:"BRCA1",type:"gene"}, node {id:"DNA repair",type:"pathway"}, edge {source:"BRCA1",target:"DNA repair",type:"inhibits"}
text "PIK3CA activates PI3K, targeted by alpelisib" → node {id:"PIK3CA",type:"gene"}, node {id:"PI3K",type:"pathway"}, node {id:"alpelisib",type:"drug"}, edges source-target
text "HER2 amplification drives RTK signaling, targeted by trastuzumab" → nodes and edges
CRITICAL: Every gene, pathway, drug mentioned must be a node. Every stated relationship must be an edge.
Types: node types = gene/pathway/targetable/drug. Edge types = activates/inhibits/targets.
Split text into labeled sections preserving original text verbatim.
NUMBERS RULE: If source states "approximately 40% of cases" for mutation frequency, include that in section content verbatim — but do NOT create chart data from it. Chart/waterfall data is for fully structured numeric arrays only.

Return ONLY: {"sections":[{"heading":"SHORT","content":"VERBATIM"}],"network":{"nodes":[{"id":"NAME","type":"gene|pathway|targetable|drug"}],"edges":[{"source":"ID","target":"ID","type":"activates|inhibits|targets"}]}}""",
        "max_tokens": 80000,
    },

    "staging": {
        "prompt": """Extract TNM staging categories and stage groups with exact size/description from text.
Examples: text "T1 ≤20mm" → {"category":"T1","description":"Tumor ≤20 mm"}
text "N0: no regional lymph node metastasis" → {"category":"N0","description":"No regional lymph node metastasis"}
text "Stage IA: T1 N0 M0" → {"stage":"IA","t":"T1","n":"N0","m":"M0"}

SURVIVAL CHART RULES (STRICT):
- Only extract chart.os values if the source text states an EXACT 5-year survival % for a SPECIFIC stage.
  GOOD: "5-year OS for stage I is 99%, stage II 85%, stage III 55%" → os:[99,85,55]
  BAD: "Stage IV prognosis is generally poor" → do NOT invent a number. Use null for that stage.
  BAD: "30%-78% depending on substage" → do NOT use 30 or 78. This is a RANGE across substages, not a single value.
  BAD: "KLASS-01 trial showed 94.2% for T1 disease" → this is a surgical trial stat. Do NOT use it as "Stage I OS = 94".
- If source gives a range like "30-78%" and you need individual stage values, ALL those stages are null.
- If source says "5-year OS: stage II 85%" → {stages:["II"],os:[85]}
- If source says nothing about 5-year OS → chart is: {stages:[],os:[]}
- A chart with all null os values is PREFERABLE to a chart with invented numbers. Output empty arrays.

Return ONLY: {"sections":[{"heading":"TNM","content":"VERBATIM"}],"t_stages":[...],"n_stages":[...],"m_stages":[...],"stage_groups":[...],"chart":{"stages":["I","II","III","IV"],"os":[null,null,null,null]}}""",
        "max_tokens": 80000,
    },

    "complications": {
        "prompt": """Extract complications as structured cards from clinical text.
Examples: text "Lymphedema: educate patients, monitor, refer for management" → {"name":"Lymphedema","detail":"VERBATIM","severity":"moderate"}
text "Neutropenia occurs in 40% of patients" → {"name":"Neutropenia","detail":"VERBATIM","incidence":"40%","severity":"severe"}

NUMBERS RULE: Set incidence to null UNLESS source text says EXACTLY "X% of patients" or "incidence of X%".
- "Common complication" → incidence:null
- "Occurs frequently" → incidence:null
- "Approximately 40%" → incidence:"40%"
- "3-5 months" is NOT a percentage → do not record as incidence
Split details from management. If data has disease_related and treatment_related keys, process each.
Chart: labels and values are for graphing complication rates. Only include items where incidence is NOT null. If ALL cards have incidence=null, chart is {labels:[],values:[]}.

Return ONLY: {"sections":[{"heading":"Complications","content":"VERBATIM"}],"cards":[{"name":"Name","detail":"VERBATIM","incidence":"NN% or null","severity":"mild|moderate|severe"}],"chart":{"labels":[],"values":[]}}""",
        "max_tokens": 80000,
    },

    "prognosis": {
        "prompt": """Extract survival data and prognostic factors as structured data.

SURVIVAL CHART RULES (STRICT — CLINICALLY CRITICAL):
Only extract chart.os numbers if EVERY one of these conditions is met:
1. Source text states "5-year overall survival" or "5-year OS" for a SPECIFIC stage
2. The exact percentage number appears verbatim (e.g., "99%", "85%", "28%")
3. The number applies to the GENERAL population, not just a specific trial

DO NOT extract if:
- Source says "median OS 3-5 months" → these are MONTHS, not 5-year %. Chart = null.
- Source says "poor prognosis" without number → null
- Source says "30%-78% depending on substage" → this is a RANGE, not single values. All stages = null.
- Source gives a surgical trial stat (e.g., "94.2% in KLASS-01") → this is trial-specific, not general.
- Source says "13-15 months median OS" → months, not %. null.
- Source says "OS at 1 year: 45%" → this is 1-year OS, not 5-year OS. null.

SELF-AUDIT: For each number in chart.os, write a mental citation: "The source says X% 5-year OS for stage Y." If you can't complete that sentence, the number is null.

Examples:
text "5-year OS: stage I 99%, stage II 85%, stage III 55%, stage IV 28%" → chart.os:[99,85,55,28]
text "Stage IV median OS 13-15 months; best supportive care yields 3-5 months" → ALL STAGES NULL. No 5-year OS stated.
text "Stage I: 94.2% in KLASS-01. Stage II/III: 30%-78% range." → ALL STAGES NULL. Trial-stat + range, not general.

Prognostic factors: Mark impacts as Favorable/Unfavorable/Variable. Details verbatim.

Return ONLY: {"sections":[{"heading":"Prognosis","content":"VERBATIM"}],"chart":{"stages":["I","II","III","IV"],"os":[null,null,null,null]},"factors":[{"factor":"Name","impact":"Favorable|Unfavorable","detail":"VERBATIM"}]}""",
        "max_tokens": 80000,
    },

    "surveillance": {
        "prompt": """Restructure surveillance/follow-up into timeline items. Extract time intervals verbatim.
Examples: text "Year 1-2: every 3-4 months, clinical exam + mammogram" → {"title":"Year 1-2: Every 3-4 months","body":"Clinical exam, mammogram","icon":"bi-calendar-check"}
text "Year 3-5: every 6 months" → {"title":"Year 3-5: Every 6 months","body":"Clinical exam","icon":"bi-calendar2-check"}
text "Annual mammogram after 5 years" → {"title":"Year 5+: Annual","body":"Mammogram, clinical exam","icon":"bi-calendar3"}
No numbers to extract — timeline items are text only.

Return ONLY: {"sections":[{"heading":"Surveillance","content":"VERBATIM"}],"timeline":[{"title":"Time period","body":"Actions","icon":"bi-calendar-check"}]}""",
        "max_tokens": 80000,
    },

    "follow_up": {
        "prompt": """Restructure follow-up plan into timeline and late effects. Extract intervals and effects verbatim.
Examples: text "Annual mammogram year 1-5" → timeline item
text "Cardiotoxicity screening due to anthracycline exposure" → {"name":"Cardiotoxicity","detail":"VERBATIM"}
text "Lymphedema surveillance" → {"name":"Lymphedema","detail":"VERBATIM"}
No numbers to extract — timeline items are text, late effects are descriptive.

Return ONLY: {"sections":[{"heading":"Follow-Up","content":"VERBATIM"}],"timeline":[{"title":"Period","body":"Actions","icon":"bi-calendar2-check"}],"late_effects":[{"name":"Effect","detail":"VERBATIM"}]}""",
        "max_tokens": 80000,
    },

    "clinical_features": {
        "prompt": """Extract symptoms with frequency percentages and alarm/red flag indicators.
Examples: text "Breast lump present in 70% of cases" → {"name":"Breast lump","frequency":"70%","alarm":false,"detail":"VERBATIM"}
text "Peau d'orange (inflammatory breast cancer) in 10%" → {"name":"Peau d'orange","frequency":"10%","alarm":true,"detail":"VERBATIM"}
text "Pain is a common presenting symptom" → {"name":"Pain","frequency":"Common","alarm":false,"detail":"VERBATIM"}

CHART RULES (STRICT):
- Only include symptoms in chart.values where frequency is an EXACT number (e.g., "70%").
- If frequency is "common", "often", "frequent", or null → do NOT add to chart.values. Keep in symptoms list only.
- chart.labels and chart.values must be parallel arrays of equal length.
- If ZERO symptoms have exact numeric frequency, chart is {labels:[],values:[]}.

Mark alarm=true ONLY for red flags/warning signs/urgent presentations.

Return ONLY: {"sections":[{"heading":"Symptoms","content":"VERBATIM"}],"symptoms":[{"name":"S","detail":"VERBATIM","frequency":"NN% or text","alarm":false}],"alarms":[{"name":"Red Flag","detail":"VERBATIM"}],"chart":{"labels":[],"values":[]}}""",
        "max_tokens": 80000,
    },

    "risk_factors": {
        "prompt": """Structure risk factors with attributable risk. Extract factor, type, strength, detail.
Examples: text "BRCA1 mutation, genetic, OR 11-45, 5-10% of all breast cancers" → {"factor":"BRCA1 mutation","type":"Genetic","strength":"High","detail":"VERBATIM"}
text "Alcohol consumption, lifestyle, RR 1.1 per 10g/day" → {"factor":"Alcohol","type":"Lifestyle","strength":"Moderate","detail":"VERBATIM"}
text "Family history" → {"factor":"Family history","type":"Genetic","strength":"High","detail":"VERBATIM"}

WATERFALL CHART RULES (STRICT):
- waterfall.values must be EXACT attributable risk percentages stated verbatim in source.
- "5-10% of all breast cancers" = RANGE, not a single value → null for waterfall. Include in detail text only.
- If source doesn't state exact attributable risk for a factor → do NOT include that factor in waterfall.
- waterfall.values, waterfall.labels, and waterfall.types must be parallel arrays of equal length.
- If ZERO factors have exact numeric attributable risk, waterfall is {labels:[],values:[],types:[]}.
- Factor strength (High/Moderate/Low) is NOT a numeric value → do not put in waterfall.values.
Strength based on OR/RR stated: OR>5 = High, OR 2-5 = Moderate, OR<2 = Low.

Return ONLY: {"sections":[{"heading":"Genetic","content":"VERBATIM"}],"cards":[{"factor":"Name","type":"Genetic|Lifestyle|Environmental|Demographic|Medical|Hormonal","strength":"High|Moderate|Low","detail":"VERBATIM"}],"waterfall":{"labels":[],"values":[],"types":[]}}""",
        "max_tokens": 80000,
    },

    "management_principles": {
        "prompt": """Convert management principles into structured decision cards and flowchart data.
Split by intent (curative/palliative/adjuvant). Extract decision nodes from text.
Examples: text "PS 0-1 patients receive curative intent chemotherapy" → decision node PS 0-1, treatment node chemotherapy
text "Patients with metastatic disease receive palliative systemic therapy" → decision node, treatment node
text "MDT review is mandatory before treatment" → {"card":{"title":"MDT","detail":"VERBATIM"}}

Return ONLY: {"sections":[{"heading":"Overview","content":"VERBATIM"}],"flowchart":{"nodes":[{"id":"n1","label":"Decision","type":"decision|treatment|outcome"}],"edges":[{"source":"n1","target":"n2","label":"criteria"}]},"cards":[{"title":"Intent","detail":"VERBATIM","color":"#10b981|#f59e0b|#6366f1"}]}""",
        "max_tokens": 80000,
    },

    "management_pathways": {
        "prompt": """Convert treatment decision pathways into flowchart nodes and edges from the structured pathway data.
The input is a list of pathway objects with pathway_id, title, branching_basis, nodes (each node has criteria, options, adjuvant_logic).
For each pathway, create decision nodes (criteria) and treatment nodes (options/recommendations), connected by edges with labels.
Example: pathway with criteria "ER+/HER2-" → decision node, "Endocrine therapy + CDK4/6 inhibitor" → treatment node, edge with label "Yes"
If adjuvant_logic states "if node-positive" → additional decision node branching from treatment node.

Return ONLY: {"sections":[{"heading":"Pathway Title","content":"VERBATIM"}],"flowcharts":[{"title":"Name","nodes":[{"id":"unique_id","label":"Criteria/Options text","type":"decision|treatment"}],"edges":[{"source":"from_id","target":"to_id","label":"Decision label"}]}]}""",
        "max_tokens": 80000,
    },

    "surgery": {
        "prompt": """Structure surgery details into procedure decision cards. Split role from procedures from principles.
Examples: text "Wide local excision for T1-T2 tumors, contraindicated in multicentric disease" → {"name":"Wide local excision","condition":"T1-T2 tumors","contraindications":"Multicentric disease","detail":"VERBATIM"}
text "Mastectomy indicated for T3-T4, multicentric disease, or patient preference" → {"name":"Mastectomy","condition":"T3-T4 / multicentric","detail":"VERBATIM"}
text "Sentinel node biopsy is standard for clinically node-negative axilla" → {"name":"SLNB","condition":"cN0","detail":"VERBATIM"}
NUMBERS RULE: If source states complication rates (e.g., "mortality rate 5%"), include in detail verbatim but do NOT create chart data. Chart/values are for enumerated arrays only.

Return ONLY: {"sections":[{"heading":"Surgery","content":"VERBATIM"}],"cards":[{"name":"Procedure","condition":"When applicable","contraindications":"When not","detail":"VERBATIM"}]}""",
        "max_tokens": 80000,
    },

    "radiation_therapy": {
        "prompt": """Extract RT dose details including total dose (Gy), fractions, treatment sites, timing.
Examples: text "50 Gy in 25 fractions over 5 weeks to the whole breast" → {"label":"Whole breast","total_dose":50,"fractions":25,"body":"50 Gy / 25 fractions / 5 weeks"}
text "Boost of 10-16 Gy in 5-8 fractions to tumor bed" → {"label":"Tumor bed boost","total_dose":14,"fractions":7,"body":"10-16 Gy / 5-8 fractions"}
text "Accelerated partial breast irradiation: 38.5 Gy in 10 fractions BID" → {"label":"APBI","total_dose":38.5,"fractions":10,"body":"38.5 Gy / 10 fractions BID"}

Return ONLY: {"sections":[{"heading":"RT","content":"VERBATIM"}],"gauges":[{"label":"Tot Dose","total_dose":NN,"fractions":NN,"unit":"Gy"}],"timeline":[{"title":"Regimen","body":"Dose / fractions / timing","icon":"bi-lightning-charge"}]}""",
        "max_tokens": 80000,
    },

    "systemic_therapy": {
        "prompt": """Structure systemic therapy into treatment line cards and timeline. Extract drug names, combinations, and settings.
Examples: text "1st line: AC-T (doxorubicin + cyclophosphamide x4 → paclitaxel x12) for adjuvant" → {"name":"AC-T","line":"1st","setting":"Adjuvant","drugs":"Doxorubicin,Cyclophosphamide,Paclitaxel","detail":"VERBATIM"}
text "Pertuzumab + trastuzumab + docetaxel for HER2+ metastatic" → {"name":"THP","line":"1st","setting":"Metastatic","drugs":"Pertuzumab,Trastuzumab,Docetaxel","detail":"VERBATIM"}
text "T-DM1 for residual disease post-neoadjuvant" → {"name":"T-DM1","setting":"Post-neoadjuvant","drugs":"T-DM1","detail":"VERBATIM"}
NUMBERS RULE: If source states OS/PFS/HR stats for a regimen, include them in detail verbatim. Do NOT create separate chart data for them. Chart/timeline/chart data is for enumerated arrays only.

Return ONLY: {"sections":[{"heading":"Systemic","content":"VERBATIM"}],"cards":[{"name":"Regimen","setting":"Setting","drugs":"Drug1,Drug2","detail":"VERBATIM"}],"timeline":[{"title":"Line","body":"Regimens","icon":"bi-1-circle-fill|bi-2-circle-fill|bi-3-circle-fill"}]}""",
        "max_tokens": 80000,
    },

    "clinical_pearls": {
        "prompt": """Categorize clinical pearls by topic. Preserve text verbatim. Categories: Diagnosis, Staging, Treatment, Prognosis, Complications, Supportive Care, Follow-up, Pearls.
Example: text "Always check ER/PR/HER2 before starting systemic therapy" → {"text":"VERBATIM","category":"Treatment"}
text "LCIS is a risk factor, not a malignancy" → {"text":"VERBATIM","category":"Diagnosis"}
text "5-year OS for stage I is >95%" → {"text":"VERBATIM","category":"Prognosis"}

Return ONLY: {"sections":[{"heading":"Pearls","content":"VERBATIM"}],"cards":[{"text":"VERBATIM","category":"Diagnosis|Staging|Treatment|Prognosis|Complications|Pearls"}]}""",
        "max_tokens": 80000,
    },
}
