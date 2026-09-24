---
name: indonesia-auto-benchmark
description: Research and compare digital capabilities across automotive brand websites in Indonesia. Use this skill when the user provides multiple automotive brands or URLs and asks for a digital benchmark, website capability comparison, customer journey comparison, best-practice analysis, innovation scan, competitive digital analysis, or presentation of automotive website capabilities.
---

# Indonesia Automotive Digital Benchmark

## Purpose

Use this skill to perform structured comparative research on automotive brand websites in Indonesia.

The objective is to understand what customers can actually DO through each brand's digital ecosystem and to compare those capabilities across brands.

Do not perform a superficial website review.

Do not primarily evaluate visual design.

Focus on FUNCTIONAL CAPABILITIES.

Examples include:

- model discovery
- vehicle comparison
- configurators
- pricing
- finance
- test-drive booking
- request-a-quote
- dealer integration
- vehicle inventory
- ecommerce
- online reservation
- aftersales
- service booking
- connected-car services
- EV tools
- charging services
- apps
- customer accounts
- personalisation
- conversational assistance
- AI functionality

---

# When to activate this skill

Use this skill when the user:

- provides two or more automotive websites for comparison
- names multiple automotive brands in Indonesia
- requests a competitor website benchmark
- requests digital capability benchmarking
- asks which automotive brands offer specific online functionality
- asks what new or innovative functionality brands are introducing
- requests a benchmark PowerPoint or comparative report
- requests best practices or white spaces across automotive websites

Do not activate it for:

- general vehicle specification comparisons
- vehicle purchase recommendations
- car price comparisons without a digital-experience component
- automotive news summaries
- general brand strategy questions unrelated to digital capabilities

---

# Default geographic scope

Indonesia.

Prioritise:

1. Official Indonesian brand websites.
2. Official Indonesian model microsites.
3. Official Indonesian digital services linked by the brand.
4. Official apps or connected services clearly available to Indonesian customers.

Do not attribute functionality from another country to Indonesia.

Never assume that functionality available globally is also available in Indonesia.

Classify external functionality as:

- Local Indonesian capability
- Linked external/global capability
- Global capability not confirmed in Indonesia

---

# Research principle

Analyse CAPABILITY BY CAPABILITY rather than BRAND BY BRAND.

Do not simply produce sections such as:

Toyota
Honda
Mitsubishi
Hyundai

and describe their websites separately.

Instead build a common capability framework and evaluate every brand against the same framework.

Example:

VEHICLE CONFIGURATION

Toyota → capability observed
Mitsubishi → capability observed
Hyundai → capability observed
BYD → not confirmed
Honda → capability observed

Then compare what each implementation actually allows the customer to do.

---

# Before starting

Read these reference files:

references/capability-taxonomy.md

references/scoring-evidence.md

references/presentation-spec.md

Use them as the common framework for all brands.

---

# Research workflow

Follow this sequence.

## STEP 1 — Define the benchmark sample

Create a list containing:

Brand

Official Indonesian website

URLs provided by the user

Other relevant official Indonesian digital properties discovered during research

Do not start scoring capabilities until the official domains have been established.

---

## STEP 2 — Research every brand using the same framework

Investigate beyond the homepage.

Where available inspect:

- homepage
- model catalogue
- model pages
- shopping tools
- configurator
- compare tools
- pricing
- financing
- promotions
- quote request
- test-drive booking
- dealer locator
- inventory
- reservation
- ecommerce
- trade-in
- aftersales
- service booking
- parts
- accessories
- warranty
- roadside assistance
- customer accounts
- owner services
- connected-car pages
- mobile applications
- EV pages
- charging ecosystem
- AI/chat/chatbot
- search
- personalisation

Follow relevant official links.

Interact with functionality when feasible.

Do not classify a marketing claim as a capability without checking what the customer can actually do.

---

# Browser behaviour

When a browser is available, use it actively.

Do not rely only on search snippets.

Open relevant pages.

Navigate menus.

Open tools.

Select options where useful.

Inspect forms.

Inspect configurators.

Inspect calculators.

Inspect dealer tools.

Inspect customer-service tools.

Inspect linked official services.

When possible, test enough of the functionality to understand how it works without completing purchases, submitting leads or sending customer information.

Do not submit forms containing fabricated personal information.

---

# Important analytical principle

Always ask:

WHAT CAN THE CUSTOMER ACTUALLY DO?

For every capability determine:

- What does it enable?
- How far can the customer progress?
- Is it static or interactive?
- Is it transactional?
- Does it use live data?
- Does it integrate another step of the journey?
- Does it connect to a dealer?
- Does it connect to inventory?
- Does it connect to finance?
- Does it remember the user?
- Is it personalised?
- Does it continue into ownership?
- Is it genuinely available in Indonesia?

---

# Evidence dataset

Maintain a structured evidence table throughout the research.

Minimum fields:

Brand

Category

Capability

Observed status

Maturity score

Novelty classification

Short description

How it works

Customer value

URL

Page title

Evidence

Date accessed

Screenshot status

Screenshot reference

Limitations

Confidence

Use this evidence table as the single source of truth.

Do not construct conclusions directly from memory.

---

# Absence of functionality

Be conservative when stating that a capability does not exist.

Before declaring a capability absent:

1. Inspect navigation.
2. Inspect relevant model pages.
3. Inspect shopping tools.
4. Inspect ownership/aftersales.
5. Search the official domain.
6. Search for official microsites.
7. Check linked official applications where relevant.

Use:

"Not found during review"

rather than:

"Does not exist"

unless absence can be established confidently.

---

# Evidence quality

Prioritise:

1. Direct observation on official Indonesian site.
2. Official linked digital service.
3. Official Indonesian documentation.
4. Official regional/global documentation where clearly labelled.

Avoid basing capability conclusions on:

- automotive media
- SEO pages
- third-party blogs
- dealer blogs
- social posts
- aggregators

unless direct official evidence is unavailable.

If secondary evidence is used, label it.

---

# Screenshots

Screenshots are evidence, not decoration.

When screenshot or browser-capture functionality is available:

capture the specific state that demonstrates the capability.

Good example:

Configurator with model, variant, colour and price visible.

Bad example:

Generic homepage banner saying "Configure your vehicle".

Prefer screenshots showing:

- interface
- input
- functionality
- output
- integration

Where useful crop irrelevant browser areas.

Do not alter the website interface.

Do not recreate screenshots using image generation.

Do not fabricate screenshots.

For each screenshot record:

Brand

Capability

URL

Date accessed

If screenshot capture is unavailable, generate a screenshot capture list identifying exactly which page and UI state should be captured manually.

---

## Capability classification and scoring checks

Before scoring a capability, define the specific customer action being evaluated. Score the action, not the page, tool name or number of options shown.

### Separate configuration, finance and trade-in

Evaluate these as three independent capabilities, even when they appear in the same interface:

1. Vehicle configuration: the customer selects vehicle attributes such as model, trim, colour, interior, wheels, packages or accessories and sees a resulting vehicle configuration.
2. Finance simulation: the customer changes financial inputs such as down payment or loan term and sees an estimated payment or financing breakdown.
3. Trade-in: the customer can request an appraisal, receive an estimated vehicle value, or start a documented exchange process for their current car.

A field asking whether the customer has a used car does not, by itself, confirm a trade-in capability. A vehicle selector inside a finance calculator does not, by itself, prove a full configurator. A displayed vehicle price does not prove that finance can be simulated.

Record exactly which inputs the customer can change and which outputs the tool produces. Keep separate evidence URLs and scores for each of the three capabilities.

### Apply the same scoring test to every brand

For each capability, answer these questions for every brand:

- What can the customer select or enter?
- What changes on screen as a result?
- Is there a calculated price, payment, appraisal or configuration summary?
- Can the result be saved, shared, sent to a dealer or carried into another step?
- Was that next step observed, or is it only described by the brand?
- Does the function require an app, account, compatible vehicle or particular location?

Do not award different scores to two brands merely because one interface lists more steps or options. A higher score requires evidence of a more advanced customer action, output or integration.

Use these maturity thresholds consistently:

- 0: Not found after documenting the relevant pages and search paths checked.
- 1: Information, outbound contact, or a limited input without a demonstrated functional result.
- 2: Interactive configuration, calculation, or structured request with a demonstrated result or submission step.
- 3: Demonstrated integration with a subsequent customer-specific step, such as transferring the actual configuration to finance, a dealer, an order or an account. A detailed calculator alone does not automatically qualify.
- 4: Demonstrated completion and confirmation, tracking, or continuity across channels.

Use "?" when the relevant interface or result could not be inspected. Do not turn missing evidence into a score of 0. Do not assign a score of 3 or 4 from a menu label, marketing description, list of interface steps, or untested promise of integration.

### Cross-brand consistency audit

Before publishing the matrix:

1. Compare the evidence for every brand in the same row side by side.
2. For every score difference, write one sentence identifying the specific observed action that justifies it.
3. If that sentence cannot be supported by a direct URL and an observed interface state, give the brands the same supported score or mark the uncertain case "?".
4. Check that each evidence URL proves the capability named in its row. If it proves a different capability, move it to the correct row.
5. Recalculate the ten most relevant differences after correcting the matrix. Remove any insight that depended on a misclassified capability or unsupported score.

If the user challenges a classification or score, re-examine the relevant official pages, correct the entire affected matrix row and any dependent insights, and state explicitly what changed. Do not merely append a clarification while leaving contradictory scores in place.

---

## STEP 3 — Independent evidence verification (mandatory second pass)

Complete this step after the evidence table is drafted and before publishing the matrix or insights. Re-open the exact official URL for every material finding, score, and comparative difference. Verify from the page itself that it supports the precise customer action attributed to the brand; a search snippet, navigation label, old press release, generic description, or a URL with an unrelated result is insufficient for a confirmed interactive capability. When the live tool cannot be inspected, label the claim as a documented/claimed feature or partial/unknown, and state what remains untested. Do not imply that a form submission, reservation, purchase, or app function was completed when it was not.

Make a verification ledger for each material brand × capability cell with: direct canonical URL (remove tracking parameters), page title, access date, surface (website/app/linked service), exact input → visible output, observed versus described versus inferred, score, uncertainty, and whether the link was re-opened. The cited page must support the cell's category. Check model, market, dealer, device, login, and publication-date restrictions. A feature described for one model or in an older announcement cannot be generalized to all Indonesian customers without current confirmation.

Audit the matrix **row by row across every brand**, using the same definition and observation standard. For any difference of one or more score points, write an internal one-sentence justification naming the additional observed action or integration. If the evidence does not establish that difference, lower the unsupported score or use ?; do not manufacture equality when one brand has stronger observed evidence. Revisit both positive and negative claims: before marking 0, inspect navigation, model pages, shopping tools, ownership, official microsites and linked apps. If access or inspection is incomplete, use ? rather than 0.

Perform an adversarial final read of the ten differences and executive summary. For each statement ask: Does the URL prove this exact feature? Is this a tool, an informational page, or a marketing promise? Am I combining two separate capabilities or confusing an input with an output? Would the same reasoning award the same score to a competitor? Does the statement assert a completed user outcome that was not tested? Correct the evidence table and regenerate all dependent matrix cells, counts and insights whenever a mismatch is found. Never patch only the narrative.

If the verification pass cannot be completed for a material claim, exclude the claim or mark it explicitly unverified. Publish coverage limits and unresolved checks alongside the findings. This second pass reduces errors; it cannot guarantee that dynamic, gated or changing site functionality is error-free.

---

# Comparative analysis

After research is complete, build a brand × capability matrix.

Rows:

Capabilities

Columns:

Brands

Organise rows into customer-journey categories.

Use the maturity scoring system defined in:

references/scoring-evidence.md

Do not calculate an overall winner.

The purpose of the matrix is to reveal:

- common capabilities
- gaps
- advanced implementations
- distinctive functions
- emerging market patterns

---

# Insight generation

Generate insights only AFTER the evidence matrix is complete.

Prioritise statements such as:

"Only two of eight brands connect configuration directly with a finance simulation."

"Service booking is widespread, but only a minority of brands expose service pricing before dealer selection."

"A small group of brands connect the website with live or dealer-level vehicle availability."

Avoid generic statements such as:

"Digital transformation is becoming increasingly important."

Quantify patterns using the benchmark sample whenever possible.

---

# Distinctive functionality

Do not describe functionality as innovative solely because the manufacturer calls it innovative.

Determine novelty relative to the actual benchmark sample.

Use:

Table Stakes

Developing

Advanced

Distinctive

according to the methodology in scoring-evidence.md.

---

# Output behaviour

If the user asks only for an analysis:

provide the capability matrix and main findings.

If the user asks for an executive report:

provide structured findings and evidence.

If the user asks for a presentation:

create the presentation following:

references/presentation-spec.md

If presentation-creation tools are available, create the actual editable presentation.

If a reference presentation or template has been supplied, use it as the visual reference.

---

# Writing style

Write like an experienced digital automotive analyst.

Use concise sentences.

Use specific descriptions.

Use evidence.

Avoid promotional language.

Avoid generic consulting language.

Avoid AI-style rhetoric.

Avoid expressions such as:

- revolutionary
- game-changing
- redefining
- seamless experience
- cutting-edge
- robust ecosystem
- holistic
- unlocking value
- digital transformation journey

unless objectively required.

Good:

"The configurator updates pricing when the user changes the vehicle variant."

Bad:

"The platform delivers a seamless, cutting-edge digital configuration experience."

---

# Fact versus interpretation

Keep observed facts separate from interpretation.

OBSERVED:

"The website allows users to choose model, trim, colour and accessories."

INTERPRETATION:

"This creates a more complete pre-dealer configuration journey than brands that only expose static variant pages."

Never present interpretation as a directly observed fact.

---

# Quality control

Before finalising:

Confirm every brand has been evaluated using the same capability framework.

Confirm major claims have supporting URLs.

Confirm capabilities attributed to Indonesia are genuinely available in Indonesia.

Confirm scores reflect functionality rather than visual design.

Confirm screenshots actually demonstrate the claims they support.

Confirm missing capabilities were reasonably investigated.

Confirm similar functionality is labelled consistently across brands.

Confirm findings are derived from the evidence matrix.

Confirm no screenshot or functionality has been invented.

---

# Default language

Default research language:

English.

Understand content in Bahasa Indonesia.

Preserve official Indonesian names of services where useful.

Explain their meaning in English when necessary.

If the user asks for Spanish, produce the analysis in Spanish.

---

# Default deliverables

When the user requests a complete benchmark, produce:

1. Executive findings
2. Capability matrix
3. Key capability deep dives
4. Evidence log
5. Presentation if requested
6. Screenshot evidence or screenshot capture list

The PowerPoint is the primary deliverable when requested.

---

# Golden rule

Do not tell the user only what automotive websites SAY.

Determine what automotive websites ALLOW CUSTOMERS TO DO.
