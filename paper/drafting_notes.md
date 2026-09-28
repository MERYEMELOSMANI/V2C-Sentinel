# Draft evidence and IEEE preparation notes

Prepared 27 September 2026. The 17-page Word manuscript uses the official IEEE Access Word template downloaded from https://ieeeaccess.ieee.org/wp-content/uploads/2025/08/Access-Template-2024.docx. IEEE Access is the working journal target because the requested length fits its recommendation to keep articles below 20 pages. The author names and affiliations supplied by the authors have been inserted. The corresponding-author identity, email, funding statement, and author photographs remain placeholders or outstanding. The selected journal or conference must still be confirmed before submission.

Revised 28 September 2026 after repository cleanup. The title now describes budget-limited cloud confirmation rather than calling the implemented scheduler deadline-aware. The related section is titled “Deadline Evaluation,” consistent with the method: deadlines classify replay outcomes but do not control request admission. The reproducibility discussion now reflects the canonical commands, separated result directories, and saved two-level configuration. The Word manuscript was rebuilt and visually checked across all 17 pages.

## Author biography sources

- Asmaa Berdigh and Khalid El Yassini biographical notes: https://www.researchgate.net/publication/337123358_Connected_car_and_CO2_emission_overview_solutions_challenges_and_opportunities
- Asmaa Berdigh doctoral record (Moulay Ismail University, 2024): https://www.mathgenealogy.org/id.php?id=84076
- Asmaa Berdigh's 2025 in-vehicle communication publications: https://link.springer.com/book/10.1007/978-981-96-6441-2?page=2
- Khalid El Yassini publication record and ORCID: https://dblp.org/pid/191/4520
- Khalid El Yassini institutional role: https://formations.umi.ac.ma/formation/byAgXOwecydHIJwSfi64bNGpJDdsr2
- Khalid El Yassini's detailed prior-paper biography: https://ijece.iaescore.com/index.php/IJECE/article/download/32515/18178

The manuscript uses the team-supplied affiliation block. The requested author order keeps the student authors together: Meryem El Osmani and Nissrine Bestout use affiliation marker 1, Asmaa Berdigh uses marker 2 plus an asterisk, and Khalid El Yassini uses marker 3 plus an asterisk. The asterisks identify both supervisors as corresponding authors; their current email addresses still require confirmation. Public records place Asmaa Berdigh at Moulay Ismail University in the 2019 source and later list Lear Corporation, while the supplied author block assigns her to IA Laboratory at the International University of Rabat. This current affiliation should be confirmed directly with her before submission.

The two biographies use the IEEE Access template's `AU_Bios` and `AU_Bios_No Space` paragraph styles (8-point biography text). Each author name uses the template's `AU_Bios bd` bold character style. No manual font substitution or size reduction was applied.

## IEEE guidance consulted

- IEEE Access submission guidelines: https://ieeeaccess.ieee.org/authors/submission-guidelines/
- IEEE Access article preparation: https://ieeeaccess.ieee.org/authors/preparing-your-article/
- Article structure and a self-contained single-paragraph abstract up to 250 words: https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/structure-your-article/
- Reference guide: https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE_Reference_Guide.pdf
- AI-generated content disclosure: https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/

The retained template governs page geometry, two columns, title, fonts, numbered section headings, table captions above tables, and references in citation order. Venue-specific anonymity, copyright, funding, author biography, and final submission requirements still need checking. No author identity, copyright statement, funding source, or hardware-deployment evidence has been invented.

## Scientific source of truth

Draft methods: run_pipeline.py and run_two_level_experiment.py.
Draft results: results/final_two_level/summary.csv and all_runs.csv.
Recording counts and durations: results/tables/all_predictions.csv.
Splits: data/metadata/split_plan.csv.
Prior-use disclosure: paper/evaluation_protocol.md.
Development benchmark only: results/benchmarks/benchmark_results.md.

No experiments or model fitting were rerun for this draft. Only saved results and prediction records were read. Existing experiment files were not modified. The first draft deliberately centers the latest two-level experiment rather than conflating it with the earlier request-policy study.

## Corrected discrepancies

- Local model is logistic regression, saved as `models/local_lr.joblib` and described consistently in the README and experiment scripts.
- Local positive threshold is the 95th percentile on normal development data. The 90th-percentile suspicion score in the earlier protocol is a different policy parameter.
- The two-level experiment uses 150 and 300 ms reporting deadlines; replies do not override or delay level-1 warnings.
- Latest results contain one evaluated attack episode per split, not a large sample of independent attacks.
- Zero confirmed false alerts applies to the separate normal recordings, about 7.3 minutes in total; it does not imply a zero population false-alert rate.
- CANShield is by Shahriar et al., arXiv:2205.01306; the old outline attributed it incorrectly.
- CICV5G's verified journal article is Zhang et al., Scientific Data 13, 878 (2026), doi:10.1038/s41597-026-07239-7.
- ROAD reference is Verma et al., PLOS ONE 19(1), e0296879 (2024), doi:10.1371/journal.pone.0296879.
- Removed unsupported first-study claims and unverified generic references.

## Work needed before submission

1. Confirm the corresponding author, email, Asmaa Berdigh's current affiliation, author photographs, funding, and final AI-use disclosure.
2. Verify the 16-reference bibliography against the final source PDFs and add any closely related work required by the selected venue.
3. Validate artifact provenance against the training pipeline, preserve a dedicated configuration for the two-level experiment, and reconcile the earlier protocol with this later analysis.
4. Add strong-local and equal-false-alert baselines, independent attack cases and substantially longer normal recordings.
5. Test trace phase and processing-time sensitivity, and clarify whether the CICV5G delay already includes application service time.
6. Replace placeholders with author biographies and photos if IEEE Access remains the target.

## Layout verification

The packaged renderer was attempted but LibreOffice is not bundled on this Windows host. Microsoft Word was used in the background to export the actual DOCX to PDF; all 17 pages were rendered to PNG and visually reviewed. The final draft contains about 13,000 words, four figures, four tables, and 16 numbered references. Intermediate files remain in `paper/working` and are not publication deliverables. Template package preservation is documented in `paper/working/access_artifact.md`; the manuscript body, relationships, content types, and footer field were the only package parts intentionally changed.
