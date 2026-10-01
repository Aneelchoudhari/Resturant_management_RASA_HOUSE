from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.dsa.trie import Trie, CategoryIndex
from app.auth import get_current_staff, get_current_admin, require_roles

router = APIRouter(prefix="/menu", tags=["menu"])

# Only admin and manager can create or delete menu items / change prices
MENU_MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
)

# Kitchen staff can toggle availability (86 items)
MENU_AVAILABILITY_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.chef,
    models.StaffRole.inventory,
)


@router.get("/", response_model=List[schemas.MenuItemResponse])
def list_menu_items(db: Session = Depends(get_db)):
    """Public — customers and guests can browse the full menu."""
    return db.query(models.MenuItem).all()


@router.post("/", response_model=schemas.MenuItemResponse, status_code=201)
def create_menu_item(
    payload: schemas.MenuItemCreate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*MENU_MANAGEMENT_ROLES)),
):
    """Create a new menu item — admin and manager only."""
    item = models.MenuItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/search", response_model=List[schemas.MenuItemResponse])
def search_menu(q: Optional[str] = None, db: Session = Depends(get_db)):
    """Prefix autocomplete using a Trie — O(k). Empty q returns all items. Public endpoint."""
    items = db.query(models.MenuItem).all()
    if not q:
        return [schemas.MenuItemResponse.model_validate(i) for i in items]
    trie = Trie()
    for item in items:
        trie.insert(item.name, schemas.MenuItemResponse.model_validate(item))
    return trie.search_prefix(q)


@router.get("/category/{tag}", response_model=List[schemas.MenuItemResponse])
def get_by_category(tag: str, db: Session = Depends(get_db)):
    """O(1) category lookup using a hash map (CategoryIndex). Public endpoint."""
    items = db.query(models.MenuItem).all()
    index = CategoryIndex()
    index.build([schemas.MenuItemResponse.model_validate(i) for i in items])
    return index.get(tag)


@router.get("/{item_id}", response_model=schemas.MenuItemResponse)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    """Public — fetch a single menu item by ID."""
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.put("/{item_id}", response_model=schemas.MenuItemResponse)
def update_menu_item(
    item_id: int,
    payload: schemas.MenuItemUpdate,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*MENU_MANAGEMENT_ROLES)),
):
    """Update a menu item — admin and manager only. Price changes require admin."""
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    updates = payload.model_dump(exclude_unset=True)
    # Price change is admin-only even among management roles
    if "price" in updates and staff.role != models.StaffRole.admin:
        raise HTTPException(status_code=403, detail="Only admin can change menu prices")
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}/availability", response_model=schemas.MenuItemResponse)
def toggle_menu_item_availability(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*MENU_AVAILABILITY_ROLES)),
):
    """Toggle a menu item's availability — admin, manager, chef, and kitchen staff."""
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.available = 0 if item.available else 1
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),  # Admin ONLY
):
    """Delete a menu item permanently — admin only."""
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    db.delete(item)
    db.commit()
