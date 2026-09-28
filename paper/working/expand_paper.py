from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'paper/working/build_draft.py').read_text(encoding='utf-8')
s=s.replace("OUT = ROOT / 'paper/V2C_Sentinel_IEEE_Draft.docx'", "OUT = ROOT / 'paper/V2C_Sentinel_IEEE_Full_Paper.docx'")
s=s.replace("V2C_Sentinel_IEEE_Draft.md", "V2C_Sentinel_IEEE_Full_Paper.md")

helpers='''
def subheading(text): return p(text, 'Heading 2')

def figure(name,caption):
    para=d.add_paragraph()
    para.alignment=WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before=Pt(5)
    para.paragraph_format.space_after=Pt(2)
    para.paragraph_format.keep_with_next=True
    shape=para.add_run().add_picture(str(ROOT/'paper/figures'/name),width=Inches(3.34))
    shape._inline.docPr.set('descr',caption)
    cap=p(caption,'figure caption')
    cap.paragraph_format.keep_together=True
    cap.paragraph_format.space_after=Pt(7)
    num=OxmlElement('w:numPr'); ident=OxmlElement('w:numId'); ident.set(qn('w:val'),'0'); num.append(ident)
    cap._p.get_or_add_pPr().append(num)

def equation(tokens,number):
    para=d.add_paragraph()
    para.alignment=WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before=Pt(4)
    para.paragraph_format.space_after=Pt(6)
    math=OxmlElement('m:oMath')
    def run(text):
        r=OxmlElement('m:r'); t=OxmlElement('m:t'); t.text=text; r.append(t); return r
    for token in tokens:
        if isinstance(token,tuple):
            sub=OxmlElement('m:sSub'); e=OxmlElement('m:e'); e.append(run(token[0])); v=OxmlElement('m:sub'); v.append(run(token[1])); sub.append(e); sub.append(v); math.append(sub)
        else: math.append(run(token))
    para._p.append(math); para.add_run('    ('+str(number)+')')
    source.append('Equation '+str(number)+': '+str(tokens))

'''
s=s.replace("title = ",helpers+"title = ",1)
def before(prefix,code):
    global s
    pos=s.index(prefix)
    s=s[:pos]+code+'\n'+s[pos:]
def after(prefix,code):
    global s
    pos=s.index('\n',s.index(prefix))
    s=s[:pos+1]+code+'\n'+s[pos+1:]

after("p('The contribution is", """
p('Three questions organize the evaluation. First, does the local warning remain timely as the confirmation budget changes? Second, what false-alert burden is visible at each alert level? Third, how much request capacity is required for confirmation to meet an episode-onset deadline? These questions separate scheduling effects from classifier performance and prevent a low confirmation false-alert rate from being mistaken for a low total warning rate.')
""")
before("p('Verma et al.","subheading('CAN Masquerade Detection')")
after("p('Shahriar et al.","""
p('Marfo et al. [4] combine message-sequence graph representations with time-series attributes for masquerade detection on ROAD. Moriano et al. [5] compare four lightweight unsupervised detectors in an online sliding-window setting and examine the trade-off between detection capability and computational overhead. Their online evaluation is particularly relevant: timing-aware CAN detection is already an established research topic. The present study addresses an additional request-admission and delayed-confirmation mechanism, rather than claiming to introduce timely detection evaluation itself.')
subheading('Offloading and Collaborative Inference')
p('Mourad et al. [6] investigate cooperative intrusion detection in an ad hoc vehicular fog. Their formulation considers execution time, energy, and offloading survivability under mobility, and includes experiments on resource-constrained devices. Zhao et al. [7] develop a cooperative intrusion-detection offloading architecture for mobile edge computing with a deep Q-network scheduling method. These works establish that offloading intrusion analysis and considering its latency are existing directions. Our simpler token-bucket replay does not replace their optimization methods; it reports the consequences of a fixed admission rule for a labeled attack episode and two distinct alert outputs.')
p('Neurosurgeon [8] studies partitioning neural-network computation between a mobile device and the cloud to manage latency and energy. V2C-Sentinel instead runs separate classifiers at two conceptual locations and gates the second classifier on a local positive decision. There is no learned partition, intermediate neural representation, or uncertainty-based deferral rule. This distinction matters because local false negatives are excluded from cloud review, while many benign local positives can consume the request budget.')
subheading('Recorded Communication Delays and Study Position')
""")
s=s.replace('a comprehensive comparison with vehicle offloading and selective-inference methods remains future work.', 'the reviewed offloading methods are contextual references rather than reimplemented experimental baselines.')

before("p('Each input event", """
subheading('Threat Model and Alert Semantics')
p('The replay assumes an adversary capable of generating masquerading CAN traffic represented by the selected ROAD labels. The attacker can alter the content associated with legitimate traffic; the study does not simulate initial compromise, cryptographic authentication, or a live attacker. The detector observes recorded identifiers and extracted signals. Model files, local processing, and the conceptual cloud service are trusted. Attacks on the confirmation channel, adversarial model manipulation, and intentional denial of the request budget are outside the evaluated threat model.')
p('A level-1 warning means that the local score crossed its operating threshold. A level-2 confirmation means that an admitted message received a positive forest prediction. The latter is a model output, not proof of an attack. Absence of confirmation can mean that the message was not admitted, that its reply has not arrived, or that the forest predicted benign traffic. Fig. 1 shows these separate paths and the persistence of the local warning.')
figure('fig1_architecture.png','Fig. 1. Two-level replay architecture. Positive local predictions produce warnings immediately and compete for cloud admission. Recorded communication delays affect only the confirmation path.')
subheading('Feature Processing and Fixed Classifiers')
""")
before("p('For a message observed", "subheading('Admission Control and Response Timing')")
after("p('An admitted request", """
p('Let tᵢ denote the observation time of message i, τL the assumed local processing time, τC the assumed cloud processing time, and d(s) the replay delay at request time s. For a locally positive message, the warning time is given by (1). If that message is admitted, its confirmation time, conditional on a positive forest prediction, is given by (2).')
equation([('s','i'),' = ',('t','i'),' + ',('τ','L')],1)
equation([('c','i'),' = ',('s','i'),' + d(',('s','i'),') + ',('τ','C')],2)
p('Equations (1) and (2) show why an episode-level deadline is stricter than a per-request response target: a suitable message may be admitted only after the attack has already been active. There is no waiting queue for rejected requests. An eligible message without a token is skipped, and a later local positive may obtain the next token. Thus the observed confirmation delay combines event selection after onset with the delay of the selected reply.')
""")
before("p('Trace timestamps", "subheading('Delay Replay and Deadline Interpretation')")
before("p('The ROAD training", "subheading('Data Partition and Experimental Conditions')")
before("p('An attack episode", "subheading('Episode and Alert Metrics')")
after("p('An attack episode", """
p('For episode e with onset aₑ and alert level k, let Wₑ,ₖ be the set of alert times linked to positive-labeled events in that episode. Its first-detection delay is defined by (3), with the minimum of an empty set treated as infinity. Timeliness at deadline D is the condition Δₑ,ₖ ≤ D. This definition credits an alert associated with the episode even if the reply arrives after the episode has ended; its delay is still measured from onset.')
equation([('Δ','e,k'),' = min{w − ',('a','e'),': w ∈ ',('W','e,k'),'}'],3)
""")
after("p('Request totals", """
p('For exposure normalization, Nq denotes admitted requests and T denotes the combined duration in seconds of the normal and attack recording within a split. The pooled request rate is Rq = Nq/T. This is a ratio of totals, not an unweighted average of per-recording rates. Development has 418.683 s of combined exposure and test has 64.694 s. Reporting pooled rates makes communication demand comparable despite the large difference in raw recording length.')
subheading('Reproducibility and Evidence Boundaries')
p('The result grid comprises two splits, two recordings per split, five budgets, and two reporting deadlines, yielding 40 recording-level evaluations. Changing the reporting deadline reclassifies the same alert trajectory and does not constitute another independent experiment. The two-level replay is deterministic for a fixed prediction file, trace, and starting state. Consequently, the plots report observed values without confidence intervals or standard-error bars; repeated deterministic execution would not measure generalization uncertainty.')
""")
before("p('Level 1 detects", "subheading('Early Warnings and Confirmation Timeliness')")
after("p('Table II reports", "figure('fig2_latency.png','Fig. 2. First-detection delay versus request budget. Each confirmation series contains one attack episode per split. The dotted line is the assumed 5 ms local path; horizontal lines mark 150 and 300 ms. The vertical axis is logarithmic.')")
# Avoid a redundant numerical delay table; report deadline outcomes instead.
start=s.index("table('TABLE II.")
end=s.index("p('The absence of",start)
s=s[:start]+"""table('TABLE II.  TIMELY CLOUD DETECTIONS OUT OF ONE EPISODE', ['Budget\\n(req/s)','Dev\\n150 ms','Dev\\n300 ms','Test\\n150 ms','Test\\n300 ms'],[
    ['1','0/1','0/1','0/1','0/1'],['5','0/1','0/1','1/1','1/1'],['10','0/1','0/1','1/1','1/1'],['50','0/1','1/1','1/1','1/1'],['Unrestricted','1/1','1/1','1/1','1/1']], [1.05,.57,.57,.57,.57])
"""+s[end:]
s=s.replace('Table II reports first cloud-confirmation delays.', 'Fig. 2 compares first-detection delays, and Table II reports the corresponding deadline outcomes.')
before("p('No level-2 false", "subheading('False Alerts and the Meaning of Confirmation')")
after("p('No level-2 false", """
figure('fig3_false_alerts.png','Fig. 3. False-alert burden on the separate normal recordings. Rates are identical across tested budgets. Zero confirmed alerts were observed over only 438.19 s combined exposure; local warnings remain present.')
p('The normal development file contains 44 288 positive local predictions among 874 018 events, while the normal test file contains 5068 among 106 939 events. These correspond to event-level positive fractions of approximately 5.07% and 4.74%. The grouping rule transforms these dense warning streams into 387 and 48 grouped alerts, respectively. These counts explain why the grouped rates remain near one alert per second. Event-level false positives and grouped operator alerts are therefore different quantities and should not be used interchangeably.')
subheading('Communication Demand')
""")
after("p('Table III combines", """
figure('fig4_request_rates.png','Fig. 4. Actual request rates pooled over the normal and attack recording within each split. Initial token bursts and finite exposure allow small deviations from the nominal sustained budget. Unrestricted admission still queries only local positives.')
p('In the unrestricted condition, development sends 49 539 requests over 418.683 s, approximately 118.3 requests/s, and test sends 6503 over 64.694 s, approximately 100.5 requests/s. At a 50 requests/s budget, the totals correspond to approximately 49.9 and 47.5 requests/s. The smaller test rate is consistent with candidate availability as well as admission limits; the budget is not a requirement to transmit at that rate. A deployed design would also need a byte budget and a server-capacity limit.')
p('The requests demonstrate a trade-off rather than a uniformly favorable budget. Development requires unrestricted admission to meet 150 ms, whereas test meets that deadline with 5 requests/s. Selecting a recommended budget from the favorable test recording would overstate the evidence. A useful configuration must instead be selected against independently measured operating requirements and a broader distribution of attack onsets and benign demand.')
""")
before("p('The results support", "subheading('Interpretation and Operational Implications')")
after("p('The results support", """
p('A practical interface could distinguish an unconfirmed advisory from a confirmed escalation, but the present experiment does not measure operator behavior or the consequences of either action. If all local warnings trigger the same intervention as confirmations, the high local false-alert burden remains the dominant operational issue. If local warnings are hidden until confirmed, the system instead inherits the confirmation delays and loses its early-warning advantage. The alert policy is therefore part of the system specification, not a cosmetic presentation choice.')
""")
before("p('The evaluation includes", "subheading('Internal and External Validity')")
before("p('A saved development-machine", "subheading('Computation and Baseline Requirements')")
after("p('A saved development-machine", """
p('Within this queue-free timing model, increasing only the constant cloud service time by 6 ms would shift every confirmation by 6 ms without changing admission or reply order. For example, the recorded 129.8 ms test confirmation would become 135.8 ms, while the 223.6 ms development confirmation would become 229.6 ms. This is an algebraic sensitivity illustration, not an additional measured run. Load-dependent queues, changing admission, or different hardware could produce substantially different effects.')
subheading('Next Validation Steps')
p('The next evaluation should freeze the two-level configuration separately from the earlier policy study, record model and data hashes, and retain per-request selection and response logs. Multiple trace phases and independent normal sessions should test timing and false-alert stability. Local-only operation, a forest executed locally, and alternative admission policies should be compared at matched alert or communication constraints. These extensions would distinguish a useful confirmation mechanism from improvements achievable through local calibration alone.')
""")
s=s.replace('generate and revise the abstract and Sections I–VII, organize the reported repository results, prepare the reference list, and format this manuscript.', 'generate and revise the abstract and Sections I–VII, organize the reported repository results, prepare the reference list and figure-generation code, and format this manuscript. Figures 1–4 were produced with this assistance; numerical plots use saved experimental outputs.')
s=s.replace('This assistance did not generate new experimental measurements. [Authors to verify the manuscript, finalize this disclosure, and add any applicable funding acknowledgment.]', 'No new experimental measurements were generated for the manuscript. The authors remain responsible for verification of the final text, figures, and references.')
s=s.replace('“CANShield: Deep learning-based intrusion detection framework for controller area networks at the signal-level,” arXiv:2205.01306, ver. 4, Oct. 2023, doi: 10.48550/arXiv.2205.01306.', '“CANShield: Deep-learning-based intrusion detection framework for controller area networks at the signal level,” IEEE Internet Things J., vol. 10, no. 24, pp. 22111–22127, 2023, doi: 10.1109/JIOT.2023.3303271.')
needle="2026, doi: 10.1038/s41597-026-07239-7.'"
s=s.replace(needle,needle+''',
    'W. Marfo, P. Moriano, D. K. Tosh, and S. V. Moore, “Detecting masquerade attacks in controller area networks using graph machine learning,” IEEE Trans. Inf. Forensics Security, vol. 20, pp. 13127–13142, 2025, doi: 10.1109/TIFS.2025.3636019.',
    'P. Moriano, S. C. Hespeler, M. Li, and R. A. Bridges, “Evaluating lightweight unsupervised online IDS for masquerade attacks in CAN,” J. Inf. Secur. Appl., vol. 98, Art. no. 104392, 2026, doi: 10.1016/j.jisa.2026.104392.',
    'A. Mourad, H. Tout, O. A. Wahab, H. Otrok, and T. Dbouk, “Ad hoc vehicular fog enabling cooperative low-latency intrusion detection,” IEEE Internet Things J., vol. 8, no. 2, pp. 829–843, 2021, doi: 10.1109/JIOT.2020.3008488.',
    'X. Zhao, G. Huang, J. Jiang, L. Gao, and M. Li, “Task offloading of cooperative intrusion detection system based on Deep Q Network in mobile edge computing,” Expert Syst. Appl., Art. no. 117860, 2022, doi: 10.1016/j.eswa.2022.117860.',
    'Y. Kang et al., “Neurosurgeon: Collaborative intelligence between the cloud and mobile edge,” in Proc. 22nd Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS), 2017, pp. 615–629, doi: 10.1145/3037697.3037698.'
''')
# Save added image relationships and content types, retaining template styles and numbering byte for byte.
start=s.index('# Preserve all template package parts')
end=s.index("(ROOT/'paper/V2C_Sentinel_IEEE_Full_Paper.md')",start)
s=s[:start]+'''# Preserve source styling; add only manuscript body, image relationships and media.
from io import BytesIO
buffer=BytesIO(); d.save(buffer); buffer.seek(0)
editable={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
with ZipFile(REF) as original, ZipFile(buffer) as revised, ZipFile(OUT,'w',ZIP_DEFLATED) as out:
    for item in original.infolist():
        data=revised.read(item.filename) if item.filename in editable else original.read(item.filename)
        out.writestr(item,data)
    for name in revised.namelist():
        if name not in original.namelist():
            assert name.startswith('word/media/'),name
            out.writestr(name,revised.read(name))
with ZipFile(REF) as original, ZipFile(OUT) as out:
    changes=[n for n in original.namelist() if original.read(n)!=out.read(n)]
assert set(changes)<=editable, changes
''' +s[end:]
(ROOT/'paper/working/build_full_paper.py').write_text(s,encoding='utf-8')
print('Expanded manuscript builder created')
