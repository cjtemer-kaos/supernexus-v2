#!/usr/bin/env python3
"""
Precision Medicine Workflow

Professional precision medicine pipeline integrating genomics, drug response
prediction, and clinical trial matching for personalized treatment.
"""

from tooluniverse.tools import (
    gwas_get_associations_for_snp,
    OpenTargets_get_disease_id_description_by_name,
    OpenTargets_get_associated_targets_by_disease_efoId,
    FDA_get_drug_names_by_indication,
    drugbank_get_targets_by_drug_name_or_drugbank_id,
    search_clinical_trials,
    get_clinical_trial_eligibility_criteria,
)


def precision_medicine_workflow(patient_genotype: list, disease_name: str):
    """
    Precision medicine workflow integrating genomics, drug response, and clinical data.

    Args:
        patient_genotype: List of patient genetic variants (rs IDs)
        disease_name: Patient's disease condition

    Returns:
        dict: Structured results with variant associations, drug targets, and trial matches
    """
    print(f"=== Precision Medicine Workflow for {disease_name} ===")

    results = {
        "disease": disease_name,
        "variant_associations": {},
        "disease_targets": [],
        "candidate_drugs_with_target_overlap": [],
        "matching_trials": [],
    }

    # Step 1: Genomic analysis
    print(f"\n1. Analyzing patient genotype ({len(patient_genotype)} variants)...")
    for variant in patient_genotype[:3]:  # Analyze first 3 variants
        print(f"   Analyzing variant: {variant}")
        try:
            assoc = gwas_get_associations_for_snp(rs_id=variant)
            if assoc:
                print(f"     Found associations: {len(assoc) if isinstance(assoc, list) else 1}")
        except Exception:
            assoc = None
        results["variant_associations"][variant] = assoc

    # Step 2: Disease target analysis
    print("\n2. Analyzing disease targets...")
    disease_info = OpenTargets_get_disease_id_description_by_name(
        diseaseName=disease_name
    )

    if disease_info and 'data' in disease_info:
        hits = disease_info['data']['search']['hits']
        if hits:
            efo_id = hits[0]['id']
            print(f"   Disease EFO ID: {efo_id}")
            results["disease_efo"] = efo_id

            # Get associated targets
            targets = OpenTargets_get_associated_targets_by_disease_efoId(
                efoId=efo_id
            )

            if targets and 'data' in targets:
                target_data = targets['data']['disease']['associatedTargets']
                target_rows = target_data['rows']
                print(f"   Found {len(target_rows)} disease targets")
                
                # Store top targets
                for row in target_rows[:10]:
                    target_id = row.get("target", {}).get("id")
                    target_symbol = row.get("target", {}).get("approvedSymbol")
                    score = row.get("associationScore", {}).get("overall")
                    results["disease_targets"].append({
                        "id": target_id,
                        "symbol": target_symbol,
                        "score": score,
                    })

    # Step 3: Drug response prediction
    print("\n3. Predicting drug response...")
    # Map FDA drugs for disease and compute overlap with disease targets
    fda = FDA_get_drug_names_by_indication(
        indication=disease_name, limit=5, skip=0
    )
    fda_names = []
    if isinstance(fda, dict) and fda.get("results"):
        for it in fda["results"]:
            if isinstance(it, dict):
                nm = (it.get("openfda", {}) or {}).get("brand_name")
                if isinstance(nm, list) and nm:
                    fda_names.append(nm[0])
    
    print(f"   Found {len(fda_names)} FDA approved drugs")
    
    # Calculate target overlap for each drug
    disease_syms = {t.get("symbol") for t in results["disease_targets"] if t.get("symbol")}
    for nm in fda_names[:3]:
        print(f"   Analyzing drug: {nm}")
        try:
            tinfo = drugbank_get_targets_by_drug_name_or_drugbank_id(
                drug_name_or_drugbank_id=nm
            )
        except Exception:
            tinfo = None
            
        drug_targets = set()
        if isinstance(tinfo, dict):
            items = tinfo.get("targets") or tinfo.get("results") or []
        else:
            items = tinfo or []
        for t in items:
            sym = t.get("name") or t.get("target_name")
            if sym:
                drug_targets.add(sym)
        
        overlap_count = len(disease_syms & drug_targets)
        results["candidate_drugs_with_target_overlap"].append({
            "drug": nm,
            "overlap_count": overlap_count,
            "drug_targets": list(drug_targets),
        })
        print(f"     Target overlap: {overlap_count}")

    # Step 4: Clinical trial matching
    print("\n4. Finding matching clinical trials...")
    trials = search_clinical_trials(
        query_term=f"{disease_name} precision medicine",
        condition=disease_name,
        pageSize=5
    )

    if trials and 'results' in trials:
        print(f"   Found {len(trials['results'])} precision medicine trials")
        for tr in trials["results"][:3]:
            nct = tr.get("nctId")
            if not nct:
                continue
            print(f"   Analyzing trial: {nct}")
            try:
                elig = get_clinical_trial_eligibility_criteria(nct_id=nct)
                print(f"     Eligibility criteria: {len(elig) if elig else 0} items")
            except Exception:
                elig = None
            results["matching_trials"].append({
                "nctId": nct,
                "title": tr.get("title", "Unknown"),
                "eligibility": elig,
            })

    print("\n=== Precision Medicine Workflow Complete ===")
    return results


if __name__ == "__main__":
    # Example usage
    results = precision_medicine_workflow(
        patient_genotype=["rs1801133", "rs429358", "rs7412"],
        disease_name="Alzheimer's disease"
    )
    
    print(f"\nResults summary:")
    print(f"- Disease: {results['disease']}")
    print(f"- Variants analyzed: {len(results['variant_associations'])}")
    print(f"- Disease targets: {len(results['disease_targets'])}")
    print(f"- Candidate drugs: {len(results['candidate_drugs_with_target_overlap'])}")
    print(f"- Matching trials: {len(results['matching_trials'])}")

