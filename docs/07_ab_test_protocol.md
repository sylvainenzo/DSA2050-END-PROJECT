# Proposed Randomised Experiment (design only — not run)

**Title:** Does proactive inspection of flagged developments reduce water loss and disruptions?

| Element | Design |
|---|---|
| Hypothesis | H0: proactive inspection of developments flagged by Rule B does not change excess water use over the next 6 months. H1: it reduces excess use (and 311 supply complaints). |
| Population | Developments flagged "inspect" by Rule B in a given month, with actual meter reads (not in a measurement-gap month) and whole metering. |
| Unit of randomisation | Development (cluster). Not meters or residents: one crew visit affects the whole development. |
| Treatment | Crew inspection within 14 days of the flag (leak survey, valve and meter check, repair as found). |
| Control | Business as usual: inspection only after a resident complaint or routine schedule. Control developments are never denied repairs that are requested. |
| Assignment | Stratified randomisation: within borough × size third, 1:1 random allocation using a seeded random number generator; allocation recorded before outcomes are seen. |
| Primary outcome | Mean residual over 6 months (log of actual ÷ expected use, actual reads only), from the same expected-use method. |
| Secondary outcomes | Months flagged again; share of estimated reads; 311 supply complaints in the borough; water and sewer cost (USD). |
| Sample size | Spread of the 6-month mean residual across developments (test period, Jan–Jun 2023): σ = 0.177. With 80% power and α = 0.05 (two-sided): **45 developments per arm (90 total) to detect a 10% reduction**, 19 per arm (38) for 15%, 10 per arm (20) for 20%. Only 44 developments had metered actual reads in Jan–Jun 2023, so a 10% effect cannot be detected with the metered developments in this dataset alone: either target a 20% effect, enrol over several months, or first extend metering (Recommendation 1). |
| Duration | 6 months follow-up per cohort; enrol cohorts monthly for 6–12 months. |
| Analysis | Intention-to-treat; difference in means with a cluster bootstrap CI (resample developments); analysis plan registered before data collection. |
| Potential confounders / threats | Seasonality (balanced by randomisation and same calendar months); regression to the mean (a development flagged in an unusually bad month tends to look better next month even without action — the control group handles this); capital works or PACT conversion during follow-up (record and report); meter replacement changing measurement; spillover when developments share supply mains (randomise neighbouring developments together); crews knowing assignment (analyst blinded). |
| Ethical safeguards | No resident is denied service: emergency and complaint-driven repairs continue in control; no tenant-level data; no penalties for residents; results shared with residents' associations; stop rule if treatment shows clear benefit (offer to control) or harm; approval by NYCHA and an ethics committee. |
