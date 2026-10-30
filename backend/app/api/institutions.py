from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import Institution, User, UserRole, FDR
from backend.app.schemas.deposafe_schemas import InstitutionCreate, InstitutionOut, FDROut
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/institutions", tags=["Institutions"])

@router.post("", response_model=InstitutionOut, status_code=status.HTTP_201_CREATED)
def create_institution(
    inst_in: InstitutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN, UserRole.REGIONAL_OFFICER, UserRole.COMPETENT_AUTHORITY]))
):
    existing = db.query(Institution).filter(Institution.aicte_id == inst_in.aicte_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution with AICTE ID '{inst_in.aicte_id}' already registered."
        )

    inst = Institution(
        aicte_id=inst_in.aicte_id,
        name=inst_in.name,
        society_or_trust_name=inst_in.society_or_trust_name,
        category=inst_in.category,
        program_level=inst_in.program_level,
        institution_type=inst_in.institution_type,
        state=inst_in.state,
        regional_office=inst_in.regional_office,
        address=inst_in.address,
        contact_email=inst_in.contact_email,
        contact_phone=inst_in.contact_phone,
        authorized_signatory_name=inst_in.authorized_signatory_name,
        signatory_pan_or_id=inst_in.signatory_pan_or_id
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    record_audit_event(
        db=db,
        event_type="INSTITUTION_REGISTERED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={"aicte_id": inst.aicte_id, "name": inst.name, "state": inst.state}
    )

    return inst


@router.get("", response_model=List[InstitutionOut])
def list_institutions(
    q: Optional[str] = Query(None, description="Search by name, AICTE ID or society"),
    state: Optional[str] = Query(None, description="Filter by state"),
    regional_office: Optional[str] = Query(None, description="Filter by regional office"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Institution)

    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER:
        if not current_user.institution_id:
            return []
        query = query.filter(Institution.id == current_user.institution_id)
    else:
        if state:
            query = query.filter(Institution.state.ilike(f"%{state}%"))
        if regional_office:
            query = query.filter(Institution.regional_office.ilike(f"%{regional_office}%"))
        if q:
            query = query.filter(
                or_(
                    Institution.name.ilike(f"%{q}%"),
                    Institution.aicte_id.ilike(f"%{q}%"),
                    Institution.society_or_trust_name.ilike(f"%{q}%")
                )
            )

    offset = (page - 1) * page_size
    return query.order_by(Institution.name.asc()).offset(offset).limit(page_size).all()


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access information belonging to another institution"
        )

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return inst


@router.get("/{institution_id}/fdrs", response_model=List[FDROut])
def get_institution_fdrs(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access FDRs belonging to another institution"
        )

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    return db.query(FDR).filter(FDR.institution_id == institution_id).order_by(FDR.id.desc()).all()

