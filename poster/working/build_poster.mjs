import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = String.raw`C:\Users\marya\Downloads\V2C-Sentinel`;
const SKILL_DIR = String.raw`C:\Users\marya\.codex\plugins\cache\openai-primary-runtime\presentations\26.909.12148\skills\presentations`;
const TMP_DIR = path.join(workspaceDir, "poster", "working");
const FINAL_PPTX = path.join(workspaceDir, "poster", "output", "V2C_Sentinel_IEEE_A0_Poster.pptx");
const pythonExecutable = String.raw`C:\Users\marya\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`;
await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const W = 4494, H = 3179; // A0 landscape at 96 px/in: 46.8125 x 33.1146 in
const FONT = "Arial";
const C = {
  navy: "#073B66", blue: "#0066A1", cyan: "#00A6D6", orange: "#F28C28",
  ink: "#17212B", gray: "#536270", line: "#CAD7E0", pale: "#EAF4F8",
  pale2: "#F5F9FB", white: "#FFFFFF", green: "#188A68", red: "#B74636",
};

const presentation = Presentation.create({ slideSize: { width: W, height: H } });
const slide = presentation.slides.add();
slide.background.fill = C.white;

function box(x,y,w,h,fill="none",radius=0,line="none",lineWidth=0){
  return slide.shapes.add({ geometry: radius ? "roundRect" : "rect", position:{left:x,top:y,width:w,height:h}, fill, line:{fill:line,width:lineWidth}, ...(radius?{borderRadius:radius}:{}) });
}
function text(t,x,y,w,h,size,color=C.ink,bold=false,align="left",opts={}){
  const s=slide.shapes.add({geometry:"textbox",position:{left:x,top:y,width:w,height:h},fill:"none",line:{fill:"none",width:0}});
  s.text=t;
  s.text.style={typeface:FONT,fontSizePt:size,color,bold,alignment:align,verticalAlignment:opts.verticalAlignment||"top",autoFit:"shrinkText",marginLeft:opts.margin??0,marginRight:opts.margin??0,marginTop:opts.margin??0,marginBottom:opts.margin??0,breakLine:opts.breakLine??false};
  return s;
}
function section(title,x,y,w){
  text(title.toUpperCase(),x,y,w,58,35,C.blue,true);
  box(x,y+54,w,7,C.cyan);
}
function body(t,x,y,w,h,size=25,color=C.ink){ return text(t,x,y,w,h,size,color,false,"left",{margin:0}); }
async function image(imgPath,x,y,w,h,fit="contain",alt=""){
  const bytes=await fs.readFile(imgPath);
  return slide.images.add({blob:bytes,contentType:"image/png",alt,fit,position:{left:x,top:y,width:w,height:h}});
}

// Header
box(0,0,W,430,C.navy);
box(0,430,W,12,C.cyan);
text("V2C-Sentinel",120,55,1160,120,72,C.white,true);
text("A Deadline-Aware Two-Level Architecture for CAN Masquerade Detection",120,154,3200,118,48,C.white,true);
text("Meryem EL OSMANI¹ · Nissrine BESTOUT¹ · Asmaa Berdigh²* · Khalid EL YASSINI³*",120,285,3250,54,29,C.white,true);
text("¹ Master IASDO, Faculty of Sciences Meknes, Moulay Ismail University  |  ² IA Laboratory, International University of Rabat  |  ³ Computer Science Department, Faculty of Sciences Meknes, Moulay Ismail University  |  * Supervisors",120,346,4100,45,21,"#DCEBF4",false);
text("IEEE-STYLE A0 POSTER",3700,65,650,45,25,"#A9DFF0",true,"right");

// Hero band
box(0,442,W,555,C.pale2);
text("Local warning first. Cloud confirmation only when requested.",120,505,1920,86,42,C.navy,true);
body("V2C-Sentinel separates two operational decisions: an immediate level-1 warning from a local detector, and a level-2 confirmation returned through a replayed cellular-delay channel. A token bucket limits cloud requests and exposes the trade-off between confirmation speed and communication demand.",120,605,1830,210,27,C.ink);
box(120,842,560,88,C.blue,18);
text("5 ms local warning",145,862,510,45,29,C.white,true,"center");
box(705,842,560,88,C.orange,18);
text("29–31 ms best confirmation",730,862,510,45,27,C.white,true,"center");
box(1290,842,620,88,C.navy,18);
text("150 / 300 ms deadlines",1315,862,570,45,27,C.white,true,"center");
await image(path.join(workspaceDir,"poster","assets","v2c_sentinel_hero.png"),2050,472,2300,500,"contain","Generated illustration of vehicle-local detection and selective cloud confirmation");

// Column guides
const x1=120, x2=1575, x3=3030, colW=1335;
box(1490,1040,3,1940,C.line); box(2945,1040,3,1940,C.line);

// Column 1
section("Problem and contribution",x1,1040,colW);
body("CAN intrusion detection must distinguish malicious activity from legitimate vehicle traffic while producing a warning early enough to support action. A remote model can add evidence, but request admission and cellular delay determine when that evidence becomes available.",x1,1120,colW,190,25);
body("CONTRIBUTION",x1,1320,colW,36,24,C.orange);
body("• Preserves every local positive as a level-1 warning\n• Sends eligible positives to a separate cloud detector\n• Replays measured 5G delay under finite request budgets\n• Reports warning and confirmation timing separately",x1,1360,colW,220,25);

section("System architecture",x1,1600,colW);
await image(path.join(workspaceDir,"paper","figures","fig1_architecture.png"),x1,1680,colW,610,"contain","Two-level V2C-Sentinel replay architecture");

section("Data and models",x1,2325,colW);
body("ROAD CAN recordings\n• Development: 63,260 attack messages; 874,018 normal messages\n• Test: 38,003 attack messages; 106,939 normal messages\n• One evaluated attack episode and one normal recording per split",x1,2405,colW,250,24);
body("LOCAL",x1,2670,230,34,23,C.blue); body("Logistic regression; 95th-percentile attack-class threshold; assumed 5 ms processing.",x1+150,2670,colW-150,75,23);
body("CLOUD",x1,2765,230,34,23,C.orange); body("Random forest; requests admitted by token bucket; assumed 10 ms processing plus replayed cellular delay.",x1+150,2765,colW-150,82,23);

// Column 2
section("Experimental design",x2,1040,colW);
body("Chronological replay with request budgets of 1, 5, 10, 50 requests/s and an unrestricted condition. Each configuration is evaluated at 150 ms and 300 ms reporting deadlines. Local warnings remain visible regardless of cloud outcome.",x2,1120,colW,170,25);

section("Confirmation latency",x2,1320,colW);
await image(path.join(workspaceDir,"paper","figures","fig2_latency.png"),x2,1400,colW,640,"contain","First confirmation delay by request budget");
body("Development confirmation improves from 3.208 s at 1 request/s to 223.6 ms at 50 requests/s and 29.0 ms without admission limits. Test confirmation reaches 129.8 ms at 5–10 requests/s and 31.0 ms at 50 requests/s or unrestricted.",x2,2055,colW,190,25);

section("Deadline outcomes",x2,2265,colW);
const rows=[
  ["Budget","Dev 150","Dev 300","Test 150","Test 300"],
  ["1 req/s","0/1","0/1","0/1","0/1"],
  ["5 req/s","0/1","0/1","1/1","1/1"],
  ["10 req/s","0/1","0/1","1/1","1/1"],
  ["50 req/s","0/1","1/1","1/1","1/1"],
  ["Unrestricted","1/1","1/1","1/1","1/1"],
];
const tbl=slide.tables.add({rows:6,columns:5,left:x2,top:2345,width:colW,height:390,values:rows});
tbl.styleOptions={headerRow:true,bandedRows:true};
tbl.borders.assign({style:"solid",fill:C.line,width:1});
for(let r=0;r<6;r++) for(let c=0;c<5;c++) tbl.getCell(r,c).text.style={typeface:FONT,fontSizePt:r===0?21:20,color:r===0?C.white:C.ink,bold:r===0,alignment:"center"};
tbl.cells.block({row:0,column:0,rowCount:1,columnCount:5}).assign({fill:C.navy,textStyle:{fontFamily:FONT,fontSizePt:21,color:C.white,bold:true,alignment:"center"},margins:{left:8,right:8,top:6,bottom:6}});
tbl.cells.block({row:1,column:0,rowCount:5,columnCount:5}).assign({textStyle:{fontFamily:FONT,fontSizePt:20,color:C.ink,alignment:"center"},margins:{left:8,right:8,top:6,bottom:6}});
body("Cell values are timely confirmations / evaluated attack episodes. With one episode per split, these are observed case outcomes rather than population detection rates.",x2,2755,colW,120,22,C.gray);

// Column 3
section("False-alert burden",x3,1040,colW);
await image(path.join(workspaceDir,"paper","figures","fig3_false_alerts.png"),x3,1120,colW,520,"contain","Grouped false-alert burden by alert level");
body("Level 1 produced approximately 3,568 and 3,620 grouped false alerts per hour on the development and test normal recordings. Level 2 produced no observed false alerts on those two short recordings. This does not establish a zero population false-alert rate.",x3,1650,colW,180,25);

section("Communication demand",x3,1850,colW);
await image(path.join(workspaceDir,"paper","figures","fig4_request_rates.png"),x3,1930,colW,490,"contain","Cloud requests by request budget and split");
body("Unrestricted replay admitted 49,539 development requests and 6,503 test requests. Finite budgets reduce network load but can delay the first useful confirmation beyond the application deadline.",x3,2425,colW,135,25);

section("What the evidence supports",x3,2580,colW);
body("SUPPORTED\n• Immediate local warnings in both evaluated attack episodes\n• Cloud confirmation reduced observed false alerts on two normal recordings\n• Confirmation latency depends on request budget and recording",x3,2660,colW,190,23,C.ink);
body("LIMITATIONS\nOne attack episode per split; short normal exposure; assumed processing times; both models executed on the development computer; no target-vehicle or production-cloud validation.",x3,2860,colW,120,23,C.red);

// Footer
box(0,3020,W,159,C.navy);
text("Conclusion",120,3047,290,38,26,C.cyan,true);
text("Cloud assistance can strengthen alert confidence, but it cannot replace the immediate local warning. Confirmation must be reported with its admission policy, communication delay, and deadline.",410,3043,2700,65,25,C.white,true);
text("Sources: ROAD dataset [Verma et al., 2024] · CICV5G delay data [Zhang et al., 2026] · Saved V2C-Sentinel replay outputs",3200,3047,1160,55,17,"#DCEBF4",false,"right");

slide.speakerNotes.textFrame.setText(
  "Poster evidence sources:\n"+
  "1. M. E. Verma et al., A comprehensive guide to CAN IDS data and introduction of the ROAD dataset, PLOS ONE, 2024. DOI: 10.1371/journal.pone.0296879.\n"+
  "2. X. Zhang et al., 5G communication delay dataset for cloud-based vehicle planning and control, Scientific Data, 2026. DOI: 10.1038/s41597-026-07239-7.\n"+
  "3. Local project outputs: results/final_two_level/summary.csv, paper_table.csv, all_runs.csv.\n"+
  "4. Hero visual generated with OpenAI ImageGen for this poster; no text embedded in the generated image."
);

const preview = await presentation.export({ slide, format:"png", scale:0.35 });
await fs.writeFile(path.join(TMP_DIR,"poster-preview.png"),new Uint8Array(await preview.arrayBuffer()));
const layout = await slide.export({format:"layout"});
await fs.writeFile(path.join(TMP_DIR,"poster-layout.json"),await layout.text());

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR,"container_tools","artifact_tool_utils.mjs")).href);
const stagingDir=path.join(TMP_DIR,".codex-finalizer");
await fs.mkdir(stagingDir,{recursive:true});
const candidatePath=path.join(stagingDir,"candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result=await finalizePresentation({
  workspaceDir,candidatePath,finalPath:FINAL_PPTX,pythonExecutable,
  integrityValidatorPath:path.join(SKILL_DIR,"container_tools","inspect_presentation_package_integrity.py"),
  layoutValidatorPath:path.join(SKILL_DIR,"container_tools","inspect_presentation_layout_geometry.py"),
  layoutArgs:["--expected-slide-size-emu","42805350,30279975","--validate-heading-fit"],
  explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:"design",families:[FONT]},verifyArtifactToolImport:true,
  receiptPath:path.join(stagingDir,"V2C_Sentinel_IEEE_A0_Poster.validation.json"),
});
console.log(JSON.stringify({finalPath:FINAL_PPTX,result},null,2));
