from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.dsa.trie import Trie, CategoryIndex

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/", response_model=List[schemas.MenuItemResponse])
def list_menu_items(db: Session = Depends(get_db)):
    return db.query(models.MenuItem).all()


@router.post("/", response_model=schemas.MenuItemResponse, status_code=201)
def create_menu_item(payload: schemas.MenuItemCreate, db: Session = Depends(get_db)):
    item = models.MenuItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/search", response_model=List[schemas.MenuItemResponse])
def search_menu(q: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Prefix autocomplete using a Trie — O(k) traversal where k = len(q).
    Empty or missing q returns all menu items.
    """
    items = db.query(models.MenuItem).all()
    if not q:
        return [schemas.MenuItemResponse.model_validate(i) for i in items]
    trie = Trie()
    for item in items:
        trie.insert(item.name, schemas.MenuItemResponse.model_validate(item))
    return trie.search_prefix(q)


@router.get("/category/{tag}", response_model=List[schemas.MenuItemResponse])
def get_by_category(tag: str, db: Session = Depends(get_db)):
    """
    O(1) category lookup using a hash map (CategoryIndex).
    """
    items = db.query(models.MenuItem).all()
    index = CategoryIndex()
    index.build([schemas.MenuItemResponse.model_validate(i) for i in items])
    return index.get(tag)


@router.get("/{item_id}", response_model=schemas.MenuItemResponse)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.put("/{item_id}", response_model=schemas.MenuItemResponse)
def update_menu_item(item_id: int, payload: schemas.MenuItemUpdate, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    db.delete(item)
    db.commit()
