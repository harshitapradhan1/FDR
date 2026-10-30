from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import verify_password, create_access_token, get_current_user
from backend.app.models.deposafe_models import User
from backend.app.schemas.deposafe_schemas import UserLogin, Token, UserOut
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account disabled")
    
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    
    record_audit_event(
        db=db,
        event_type="USER_LOGIN",
        entity_type="USER",
        entity_id=str(user.id),
        actor_id=user.id,
        actor_role=user.role.value,
        payload={"email": user.email, "role": user.role.value}
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "institution_id": user.institution_id,
            "regional_office": user.regional_office,
            "designation": user.designation
        }
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

