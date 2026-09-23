# Final bounded SCVIC source-access check

Checked September 23, 2026, after the support diagnostic. Read-only public-source inspection; no access challenge was bypassed and no external messages were sent.

- The author-attributed [GitHub repository API](https://api.github.com/repos/IoT-CPS-Labs/SCVIC-APT-2021) and raw README returned HTTP 404.
- [DataCite's DOI record](https://api.datacite.org/dois/10.21227/g2z5-ep97) returned HTTP 200 and CC-BY-4.0 rights metadata. It had `contentUrl=null`, no related identifiers, and a DataPort landing URL rather than a public CSV download.
- The [coauthor's University of Ottawa page](https://www.site.uottawa.ca/~bkantarc/) points to DataPort and the [original article](https://ieeexplore.ieee.org/document/9803189). The article presented an interactive robot check; research browsing could not access DataPort. Cached primary DataPort metadata lists a separate test file behind sign-in.
- The inspected accessible [coauthor paper](https://arxiv.org/pdf/2208.05089) did not supply a clock correction or a row-to-execution mapping in retrieved text.

No inspected author source resolved the local 1970/2015 timestamp mixture or mapped the actual training rows to repeated executions. Descriptions of four training rounds and one test round in later non-author work do not establish a mapping for these bytes. No author-owned public test CSV was located in this bounded check; this is not a claim that no accessible copy exists anywhere.

Result: no change to SCVIC's current temporal qualification. An actual source-supported mapping or documented clock interpretation is required before fitting the unchanged D1 temporal comparison. This does not prevent separately labeled recorded-time sensitivity work, but that would not independently validate physical chronology.
