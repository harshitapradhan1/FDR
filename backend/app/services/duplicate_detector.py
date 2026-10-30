"""DepoSafe Duplicate Detection Intelligence Service.

Detects multi-layer duplicate collisions across institutions and academic years:
1. Exact Bank + FDR Number Match (composite key: bank_name + fdr_number, NOT fdr_number alone).
2. SHA-256 Identical File Collision (exact byte-level reuse across institutions/records).
3. Perceptual Hash (pHash) Hamming Distance Similarity (detects visual re-scans and template re-renders).

Statutory Label: "Relationship requiring investigation, not proof of fraud."
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import imagehash

from backend.app.models.deposafe_models import FDR, FDRDocument, Institution

class DuplicateDetector:
    PHASH_HAMMING_THRESHOLD = 8  # Hamming distance <= 8 indicates visual template reuse

    @classmethod
    def check_fdr_duplicates(
        cls,
        fdr: FDR,
        db: Session
    ) -> Dict[str, Any]:
        """
        Executes full multi-modal duplicate collision checks for an FDR instrument.
        """
        exact_bank_fdr_matches = []
        sha256_identical_matches = []
        phash_visual_matches = []

        # 1. Exact Bank + FDR Number Match (Cross-Institution or Cross-Lineage)
        cross_inst_fdrs = db.query(FDR).filter(
            FDR.bank_name == fdr.bank_name,
            FDR.fdr_number == fdr.fdr_number,
            FDR.id != fdr.id
        ).all()

        for dup in cross_inst_fdrs:
            other_inst = db.query(Institution).filter(Institution.id == dup.institution_id).first()
            exact_bank_fdr_matches.append({
                "collision_type": "EXACT_BANK_AND_FDR_NUMBER",
                "matched_fdr_id": dup.id,
                "matched_internal_id": dup.internal_fdr_id,
                "matched_fdr_number": dup.fdr_number,
                "bank_name": dup.bank_name,
                "institution_id": dup.institution_id,
                "institution_name": other_inst.name if other_inst else "Unknown",
                "aicte_id": other_inst.aicte_id if other_inst else "N/A",
                "state": other_inst.state if other_inst else "N/A",
                "status": dup.status.value,
                "reason": f"Same bank '{fdr.bank_name}' and FDR number '{fdr.fdr_number}' is already pledged by {other_inst.name if other_inst else 'another institution'}."
            })

        # 2. SHA-256 and Perceptual Hash Collisions
        latest_doc = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.desc()).first()
        if latest_doc:
            # 2a. SHA-256 exact byte match
            if latest_doc.file_hash_sha256:
                sha_dups = db.query(FDRDocument).filter(
                    FDRDocument.file_hash_sha256 == latest_doc.file_hash_sha256,
                    FDRDocument.fdr_id != fdr.id
                ).all()

                for d in sha_dups:
                    parent_fdr = db.query(FDR).filter(FDR.id == d.fdr_id).first()
                    p_inst = db.query(Institution).filter(Institution.id == parent_fdr.institution_id).first() if parent_fdr else None
                    sha256_identical_matches.append({
                        "collision_type": "BYTE_FOR_BYTE_SHA256_COLLISION",
                        "matched_document_id": d.id,
                        "matched_fdr_id": d.fdr_id,
                        "file_name": d.file_name,
                        "sha256_hash": d.file_hash_sha256,
                        "institution_id": p_inst.id if p_inst else None,
                        "institution_name": p_inst.name if p_inst else "Unknown",
                        "aicte_id": p_inst.aicte_id if p_inst else "N/A",
                        "reason": "Exact byte-for-byte identical file reused across different deposits."
                    })

            # 2b. Perceptual Hash (pHash) Hamming Distance
            if latest_doc.perceptual_hash and len(sha256_identical_matches) == 0:
                try:
                    target_hash = imagehash.hex_to_hash(latest_doc.perceptual_hash)
                    other_docs = db.query(FDRDocument).filter(
                        FDRDocument.fdr_id != fdr.id,
                        FDRDocument.perceptual_hash.isnot(None)
                    ).limit(100).all()

                    for od in other_docs:
                        try:
                            candidate_hash = imagehash.hex_to_hash(od.perceptual_hash)
                            dist = target_hash - candidate_hash  # Hamming distance
                            if dist <= cls.PHASH_HAMMING_THRESHOLD:
                                parent_fdr = db.query(FDR).filter(FDR.id == od.fdr_id).first()
                                p_inst = db.query(Institution).filter(Institution.id == parent_fdr.institution_id).first() if parent_fdr else None
                                phash_visual_matches.append({
                                    "collision_type": "PERCEPTUAL_LAYOUT_CLONE",
                                    "matched_document_id": od.id,
                                    "matched_fdr_id": od.fdr_id,
                                    "hamming_distance": dist,
                                    "institution_name": p_inst.name if p_inst else "Unknown",
                                    "reason": f"Visual template structure similarity (Hamming distance {dist} <= {cls.PHASH_HAMMING_THRESHOLD}) indicates re-scan or visual clone."
                                })
                        except Exception:
                            continue
                except Exception:
                    pass

        has_collision = bool(exact_bank_fdr_matches or sha256_identical_matches or phash_visual_matches)

        return {
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "bank_name": fdr.bank_name,
            "has_collision": has_collision,
            "exact_bank_fdr_matches": exact_bank_fdr_matches,
            "sha256_identical_matches": sha256_identical_matches,
            "phash_visual_matches": phash_visual_matches,
            "total_duplicate_flags": len(exact_bank_fdr_matches) + len(sha256_identical_matches) + len(phash_visual_matches),
            "statutory_label": "Relationship requiring investigation, not proof of fraud."
        }

