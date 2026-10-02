import pytest
from app.dsa.trie import Trie, TrieNode, CategoryIndex


# ── helpers ────────────────────────────────────────────────────────────────────

def make_item(name, category, price=10.0, tags=None):
    """Return a simple namespace object that mimics a MenuItemResponse."""
    class Item:
        pass
    item = Item()
    item.name = name
    item.category = category
    item.price = price
    item.tags = tags
    return item


def names(items):
    return {i.name for i in items}


# ── TrieNode tests ─────────────────────────────────────────────────────────────

class TestTrieNode:
    def test_initial_state(self):
        node = TrieNode()
        assert node.children == {}
        assert node.is_end is False
        assert node.items == []


# ── Trie insert / search_prefix tests ─────────────────────────────────────────

class TestTrieInsertSearch:
    def test_insert_and_exact_match(self):
        trie = Trie()
        item = make_item("Burger", "mains")
        trie.insert("Burger", item)
        result = trie.search_prefix("Burger")
        assert len(result) == 1
        assert result[0].name == "Burger"

    def test_prefix_matches_multiple_items(self):
        trie = Trie()
        burger = make_item("Burger", "mains")
        butter_chicken = make_item("Butter Chicken", "mains")
        fries = make_item("Fries", "sides")
        trie.insert("Burger", burger)
        trie.insert("Butter Chicken", butter_chicken)
        trie.insert("Fries", fries)

        result = trie.search_prefix("bu")
        assert names(result) == {"Burger", "Butter Chicken"}

    def test_prefix_single_char(self):
        trie = Trie()
        trie.insert("Fries", make_item("Fries", "sides"))
        trie.insert("Fish", make_item("Fish", "mains"))
        trie.insert("Pizza", make_item("Pizza", "mains"))

        result = trie.search_prefix("f")
        assert names(result) == {"Fries", "Fish"}

    def test_exact_word_is_also_prefix_match(self):
        trie = Trie()
        ice = make_item("Ice", "drinks")
        ice_cream = make_item("Ice Cream", "desserts")
        trie.insert("Ice", ice)
        trie.insert("Ice Cream", ice_cream)

        result = trie.search_prefix("Ice")
        assert names(result) == {"Ice", "Ice Cream"}

    def test_no_match_returns_empty(self):
        trie = Trie()
        trie.insert("Burger", make_item("Burger", "mains"))
        assert trie.search_prefix("xyz") == []

    def test_empty_prefix_returns_all(self):
        trie = Trie()
        trie.insert("Burger", make_item("Burger", "mains"))
        trie.insert("Fries", make_item("Fries", "sides"))
        trie.insert("Cola", make_item("Cola", "drinks"))

        result = trie.search_prefix("")
        assert names(result) == {"Burger", "Fries", "Cola"}

    def test_case_insensitive_insert_and_search(self):
        trie = Trie()
        item = make_item("Burger", "mains")
        trie.insert("Burger", item)

        assert len(trie.search_prefix("BURGER")) == 1
        assert len(trie.search_prefix("burger")) == 1
        assert len(trie.search_prefix("BuRgEr")) == 1

    def test_case_insensitive_prefix(self):
        trie = Trie()
        trie.insert("Pasta", make_item("Pasta", "mains"))
        trie.insert("Paneer", make_item("Paneer", "mains"))

        result = trie.search_prefix("PA")
        assert names(result) == {"Pasta", "Paneer"}

    def test_empty_trie_returns_empty(self):
        trie = Trie()
        assert trie.search_prefix("any") == []
        assert trie.search_prefix("") == []

    def test_single_char_item_name(self):
        trie = Trie()
        item = make_item("A", "misc")
        trie.insert("A", item)
        assert len(trie.search_prefix("a")) == 1
        assert trie.search_prefix("b") == []

    def test_multiple_items_same_prefix_word(self):
        # Two different items with the same name (edge case: duplicates)
        trie = Trie()
        item1 = make_item("Coke", "drinks")
        item2 = make_item("Coke", "drinks")
        trie.insert("Coke", item1)
        trie.insert("Coke", item2)
        result = trie.search_prefix("co")
        assert len(result) == 2

    def test_prefix_longer_than_any_word_returns_empty(self):
        trie = Trie()
        trie.insert("Hi", make_item("Hi", "misc"))
        assert trie.search_prefix("Hello") == []

    def test_search_does_not_mutate_trie(self):
        trie = Trie()
        trie.insert("Steak", make_item("Steak", "mains"))
        trie.search_prefix("ste")
        trie.search_prefix("ste")
        # Should still return correctly on third call
        result = trie.search_prefix("ste")
        assert len(result) == 1

    def test_reinserting_same_logical_id_updates_instead_of_duplicates(self):
        trie = Trie()
        old = make_item("Burger", "mains")
        old.id = 7
        updated = make_item("Burrito", "mains")
        updated.id = 7
        trie.insert(old.name, old)
        trie.insert(updated.name, updated)
        assert [item.name for item in trie.search_prefix("bur")] == ["Burrito"]
        assert trie.search_prefix("burge") == []

    def test_update_and_delete_prune_stale_prefixes(self):
        trie = Trie()
        item = make_item("Steak", "mains")
        item.id = 8
        trie.insert(item.name, item)
        item.name = "Salad"
        trie.update("Steak", "Salad", item)
        assert trie.search_prefix("ste") == []
        assert trie.search_prefix("sal") == [item]
        assert trie.remove("Salad", item)
        assert trie.search_prefix("sal") == []

    def test_transient_item_identity_survives_database_id_assignment(self):
        trie = Trie()
        index = CategoryIndex()
        item = make_item("Soup", "starters")
        trie.insert(item.name, item)
        index.add(item)
        item.id = 11
        item.name = "Stew"
        item.category = "mains"
        trie.update("Soup", "Stew", item)
        index.update(item)
        assert trie.search_prefix("sou") == []
        assert trie.search_prefix("ste") == [item]
        assert index.get("starters") == []
        assert index.get("mains") == [item]

    def test_large_prefix_search(self):
        trie = Trie()
        for item_id in range(10000):
            item = make_item(f"Dish {item_id:05d}", "mains")
            item.id = item_id
            trie.insert(item.name, item)
        assert len(trie.search_prefix("dish 09")) == 1000


# ── CategoryIndex tests ────────────────────────────────────────────────────────

class TestCategoryIndex:
    def test_build_and_get(self):
        index = CategoryIndex()
        items = [
            make_item("Burger", "mains"),
            make_item("Pizza", "mains"),
            make_item("Cola", "drinks"),
        ]
        index.build(items)

        result = index.get("mains")
        assert names(result) == {"Burger", "Pizza"}

    def test_get_returns_empty_for_missing_category(self):
        index = CategoryIndex()
        index.build([make_item("Burger", "mains")])
        assert index.get("desserts") == []

    def test_case_insensitive_category_key(self):
        index = CategoryIndex()
        index.build([make_item("Burger", "Mains")])
        assert len(index.get("MAINS")) == 1
        assert len(index.get("mains")) == 1

    def test_build_empty_list(self):
        index = CategoryIndex()
        index.build([])
        assert index.get("anything") == []

    def test_all_categories_sorted(self):
        index = CategoryIndex()
        index.build([
            make_item("Steak", "mains"),
            make_item("Brownie", "desserts"),
            make_item("Cola", "drinks"),
        ])
        assert index.all_categories() == ["desserts", "drinks", "mains"]

    def test_single_category_multiple_items(self):
        index = CategoryIndex()
        items = [make_item(f"Item{i}", "starters") for i in range(5)]
        index.build(items)
        assert len(index.get("starters")) == 5

    def test_rebuild_replaces_previous_index(self):
        index = CategoryIndex()
        index.build([make_item("OldItem", "mains")])
        index.build([make_item("NewItem", "desserts")])
        assert index.get("mains") == []
        assert len(index.get("desserts")) == 1

    def test_add_update_remove_and_duplicate_ids(self):
        index = CategoryIndex()
        old = make_item("Soup", "starters")
        old.id = 10
        index.add(old)
        changed = make_item("Soup", "mains")
        changed.id = 10
        index.update(changed)
        assert index.get("starters") == []
        assert index.get("mains") == [changed]
        assert index.remove(item_id=10)
        assert index.get("mains") == []
