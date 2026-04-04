import pytest
from core.model import MapModel
from core.config import TILE_DEFS, MAX_UNDO


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_model(width=5, height=5, fill_tile=0):
    m = MapModel()
    m.initialise(width, height, fill_tile, TILE_DEFS)
    return m


# ---------------------------------------------------------------------------
# initialise
# ---------------------------------------------------------------------------

class TestInitialise:
    def test_dimensions(self):
        m = make_model(10, 8)
        assert m.width == 10
        assert m.height == 8

    def test_grid_row_count(self):
        m = make_model(4, 3)
        assert len(m.grid) == 3

    def test_grid_col_count(self):
        m = make_model(4, 3)
        assert all(len(row) == 4 for row in m.grid)

    def test_fill_tile(self):
        m = make_model(3, 3, fill_tile=1)
        assert all(cell == 1 for row in m.grid for cell in row)

    def test_doors_cleared_on_reinit(self):
        m = make_model()
        m.doors[(1, 1)] = 5
        m.initialise(5, 5, 0, TILE_DEFS)
        assert m.doors == {}

    def test_undo_stack_cleared_on_reinit(self):
        m = make_model()
        m.push_undo([(0, 0, 0, 1, None, None)])
        m.initialise(5, 5, 0, TILE_DEFS)
        assert m.undo_stack == []

    def test_redo_stack_cleared_on_reinit(self):
        m = make_model()
        m.push_redo([(0, 0, 0, 1, None, None)])
        m.initialise(5, 5, 0, TILE_DEFS)
        assert m.redo_stack == []


# ---------------------------------------------------------------------------
# in_bounds
# ---------------------------------------------------------------------------

class TestInBounds:
    def test_origin_is_valid(self):
        m = make_model(5, 5)
        assert m.in_bounds(0, 0)

    def test_last_cell_is_valid(self):
        m = make_model(5, 5)
        assert m.in_bounds(4, 4)

    def test_negative_x(self):
        m = make_model(5, 5)
        assert not m.in_bounds(-1, 0)

    def test_negative_y(self):
        m = make_model(5, 5)
        assert not m.in_bounds(0, -1)

    def test_x_equals_width(self):
        m = make_model(5, 5)
        assert not m.in_bounds(5, 0)

    def test_y_equals_height(self):
        m = make_model(5, 5)
        assert not m.in_bounds(0, 5)


# ---------------------------------------------------------------------------
# set_tile
# ---------------------------------------------------------------------------

class TestSetTile:
    def test_sets_non_door_tile(self):
        m = make_model()
        m.set_tile(2, 2, 1)
        assert m.grid[2][2] == 1

    def test_door_creates_entry_with_default_zero(self):
        m = make_model()
        m.set_tile(1, 1, 2)
        assert (1, 1) in m.doors
        assert m.doors[(1, 1)] == 0

    def test_door_with_explicit_id(self):
        m = make_model()
        m.set_tile(1, 1, 2, door_id=7)
        assert m.doors[(1, 1)] == 7

    def test_door_does_not_overwrite_existing_id(self):
        m = make_model()
        m.set_tile(1, 1, 2, door_id=42)
        # set_tile again without explicit id — should keep 42
        m.set_tile(1, 1, 2)
        assert m.doors[(1, 1)] == 42

    def test_non_door_removes_door_entry(self):
        m = make_model()
        m.set_tile(1, 1, 2, door_id=5)
        m.set_tile(1, 1, 0)
        assert (1, 1) not in m.doors

    def test_floor_tile_no_door_created(self):
        m = make_model()
        m.set_tile(0, 0, 0)
        assert (0, 0) not in m.doors


# ---------------------------------------------------------------------------
# Undo / Redo stack basics
# ---------------------------------------------------------------------------

class TestUndoRedoStack:
    def test_push_and_pop_undo(self):
        m = make_model()
        changes = [(1, 2, 0, 1, None, None)]
        m.push_undo(changes)
        assert m.pop_undo() == changes

    def test_pop_undo_empty_returns_none(self):
        m = make_model()
        assert m.pop_undo() is None

    def test_push_and_pop_redo(self):
        m = make_model()
        changes = [(0, 0, 1, 0, None, None)]
        m.push_redo(changes)
        assert m.pop_redo() == changes

    def test_pop_redo_empty_returns_none(self):
        m = make_model()
        assert m.pop_redo() is None

    def test_push_undo_clears_redo(self):
        m = make_model()
        m.push_redo([(0, 0, 0, 1, None, None)])
        m.push_undo([(1, 1, 0, 1, None, None)])
        assert m.redo_stack == []

    def test_max_undo_limit_enforced(self):
        m = make_model()
        for i in range(MAX_UNDO + 10):
            m.push_undo([(i, 0, 0, 1, None, None)])
        assert len(m.undo_stack) == MAX_UNDO

    def test_clear_undo_redo_empties_both(self):
        m = make_model()
        m.push_undo([(0, 0, 0, 1, None, None)])
        m.push_redo([(0, 0, 1, 0, None, None)])
        m.clear_undo_redo()
        assert m.undo_stack == []
        assert m.redo_stack == []

    def test_redo_to_undo_does_not_clear_redo(self):
        m = make_model()
        redo_entry = [(1, 1, 0, 1, None, None)]
        m.push_redo(redo_entry)
        m.redo_to_undo(redo_entry)
        assert len(m.undo_stack) == 1
        assert len(m.redo_stack) == 1


# ---------------------------------------------------------------------------
# begin_action / record_before / commit_action
# ---------------------------------------------------------------------------

class TestActionRecording:
    def test_commit_returns_false_when_nothing_changed(self):
        m = make_model()
        m.begin_action()
        m.record_before(0, 0)
        # grid[0][0] is already 0 — no actual change
        result = m.commit_action()
        assert result is False
        assert m.undo_stack == []

    def test_commit_returns_true_when_tile_changed(self):
        m = make_model()
        m.begin_action()
        m.record_before(0, 0)
        m.set_tile(0, 0, 1)
        result = m.commit_action()
        assert result is True
        assert len(m.undo_stack) == 1

    def test_record_before_only_snapshots_first_time(self):
        m = make_model()
        m.begin_action()
        m.record_before(0, 0)
        m.set_tile(0, 0, 1)
        # second record_before must not overwrite the snapshot
        m.record_before(0, 0)
        m.set_tile(0, 0, 3)
        m.commit_action()
        old_tile = m.undo_stack[-1][0][2]
        assert old_tile == 0  # original value, not 1

    def test_commit_empty_action_returns_false(self):
        m = make_model()
        m.begin_action()
        result = m.commit_action()
        assert result is False

    def test_commit_clears_cell_before_buffer(self):
        m = make_model()
        m.begin_action()
        m.record_before(0, 0)
        m.set_tile(0, 0, 1)
        m.commit_action()
        # After commit, buffer should be empty
        assert m._cell_before == {}


# ---------------------------------------------------------------------------
# apply_changes
# ---------------------------------------------------------------------------

class TestApplyChanges:
    def test_forward_apply_sets_new_tile(self):
        m = make_model()
        changes = [(1, 1, 0, 1, None, None)]
        m.apply_changes(changes, reverse=False)
        assert m.grid[1][1] == 1

    def test_forward_apply_returns_affected_cells(self):
        m = make_model()
        changes = [(1, 1, 0, 1, None, None)]
        affected = m.apply_changes(changes, reverse=False)
        assert (1, 1) in affected

    def test_reverse_apply_restores_old_tile(self):
        m = make_model()
        m.grid[1][1] = 1
        changes = [(1, 1, 0, 1, None, None)]
        m.apply_changes(changes, reverse=True)
        assert m.grid[1][1] == 0

    def test_forward_apply_sets_door(self):
        m = make_model()
        changes = [(2, 2, 0, 2, None, 5)]
        m.apply_changes(changes, reverse=False)
        assert m.grid[2][2] == 2
        assert m.doors[(2, 2)] == 5

    def test_reverse_apply_removes_door(self):
        m = make_model()
        m.doors[(2, 2)] = 5
        changes = [(2, 2, 0, 2, None, 5)]
        m.apply_changes(changes, reverse=True)
        assert m.grid[2][2] == 0
        assert (2, 2) not in m.doors

    def test_multiple_cells_applied(self):
        m = make_model()
        changes = [
            (0, 0, 0, 1, None, None),
            (1, 0, 0, 1, None, None),
            (2, 0, 0, 1, None, None),
        ]
        affected = m.apply_changes(changes, reverse=False)
        assert len(affected) == 3
        assert m.grid[0][0] == 1
        assert m.grid[0][1] == 1
        assert m.grid[0][2] == 1


# ---------------------------------------------------------------------------
# flood_fill
# ---------------------------------------------------------------------------

class TestFloodFill:
    def test_fills_entire_uniform_grid(self):
        m = make_model(3, 3, fill_tile=0)
        m.begin_action()
        modified = m.flood_fill(0, 0, 1)
        assert len(modified) == 9
        assert all(m.grid[y][x] == 1 for y in range(3) for x in range(3))

    def test_same_tile_returns_empty_list(self):
        m = make_model(3, 3, fill_tile=0)
        m.begin_action()
        result = m.flood_fill(0, 0, 0)
        assert result == []

    def test_out_of_bounds_start_returns_empty(self):
        m = make_model(3, 3)
        m.begin_action()
        result = m.flood_fill(10, 10, 1)
        assert result == []

    def test_does_not_cross_different_tile(self):
        m = make_model(3, 3, fill_tile=0)
        # Wall in middle column
        for y in range(3):
            m.grid[y][1] = 1
        m.begin_action()
        modified = m.flood_fill(0, 0, 3)
        xs = [x for x, _ in modified]
        assert all(x == 0 for x in xs)

    def test_partial_fill_isolated_region(self):
        m = make_model(3, 1, fill_tile=0)
        m.grid[0][1] = 1  # Row: [0, 1, 0]
        m.begin_action()
        modified = m.flood_fill(2, 0, 3)
        assert len(modified) == 1
        assert m.grid[0][2] == 3
        assert m.grid[0][0] == 0

    def test_fill_records_before_for_undo(self):
        m = make_model(2, 2, fill_tile=0)
        m.begin_action()
        m.flood_fill(0, 0, 1)
        result = m.commit_action()
        assert result is True
        assert len(m.undo_stack) == 1


# ---------------------------------------------------------------------------
# validate_before_save
# ---------------------------------------------------------------------------

class TestValidateBeforeSave:
    def test_valid_state_does_not_raise(self):
        m = make_model()
        m.set_tile(1, 1, 2, door_id=0)
        m.validate_before_save()  # should not raise

    def test_empty_map_does_not_raise(self):
        m = make_model()
        m.validate_before_save()

    def test_door_out_of_bounds_raises(self):
        m = make_model()
        m.doors[(99, 99)] = 0
        with pytest.raises(ValueError, match="außerhalb"):
            m.validate_before_save()

    def test_door_on_non_door_tile_raises(self):
        m = make_model()
        # (1,1) is floor (tile 0), not door
        m.doors[(1, 1)] = 0
        with pytest.raises(ValueError, match="Tür-Zelle"):
            m.validate_before_save()

    def test_negative_door_id_raises(self):
        m = make_model()
        m.set_tile(1, 1, 2)
        m.doors[(1, 1)] = -1
        with pytest.raises(ValueError, match=">= 0"):
            m.validate_before_save()


# ---------------------------------------------------------------------------
# bresenham
# ---------------------------------------------------------------------------

class TestBresenham:
    def _pts(self, *args):
        return list(MapModel.bresenham(*args))

    def test_single_point(self):
        assert self._pts(2, 3, 2, 3) == [(2, 3)]

    def test_horizontal_line_left_to_right(self):
        assert self._pts(0, 0, 4, 0) == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]

    def test_horizontal_line_right_to_left(self):
        assert self._pts(4, 0, 0, 0) == [(4, 0), (3, 0), (2, 0), (1, 0), (0, 0)]

    def test_vertical_line_top_to_bottom(self):
        assert self._pts(0, 0, 0, 3) == [(0, 0), (0, 1), (0, 2), (0, 3)]

    def test_vertical_line_bottom_to_top(self):
        assert self._pts(0, 3, 0, 0) == [(0, 3), (0, 2), (0, 1), (0, 0)]

    def test_diagonal_line(self):
        assert self._pts(0, 0, 3, 3) == [(0, 0), (1, 1), (2, 2), (3, 3)]

    def test_starts_at_start_point(self):
        pts = self._pts(1, 2, 5, 4)
        assert pts[0] == (1, 2)

    def test_ends_at_end_point(self):
        pts = self._pts(1, 2, 5, 4)
        assert pts[-1] == (5, 4)

    def test_no_duplicate_points(self):
        pts = self._pts(0, 0, 6, 3)
        assert len(pts) == len(set(pts))

    def test_negative_slope(self):
        pts = self._pts(0, 3, 3, 0)
        assert pts[0] == (0, 3)
        assert pts[-1] == (3, 0)


# ---------------------------------------------------------------------------
# rect_outline
# ---------------------------------------------------------------------------

class TestRectOutline:
    def test_single_cell(self):
        m = make_model(5, 5)
        assert set(m.rect_outline(2, 2, 2, 2)) == {(2, 2)}

    def test_2x2_rect(self):
        m = make_model(5, 5)
        assert set(m.rect_outline(0, 0, 1, 1)) == {(0, 0), (1, 0), (0, 1), (1, 1)}

    def test_3x3_has_8_perimeter_cells(self):
        m = make_model(5, 5)
        cells = set(m.rect_outline(0, 0, 2, 2))
        assert len(cells) == 8

    def test_3x3_center_excluded(self):
        m = make_model(5, 5)
        cells = set(m.rect_outline(0, 0, 2, 2))
        assert (1, 1) not in cells

    def test_reversed_corners_same_result(self):
        m = make_model(5, 5)
        a = set(m.rect_outline(0, 0, 3, 3))
        b = set(m.rect_outline(3, 3, 0, 0))
        assert a == b

    def test_clips_out_of_bounds_cells(self):
        m = make_model(3, 3)
        cells = set(m.rect_outline(1, 1, 5, 5))
        for x, y in cells:
            assert m.in_bounds(x, y)

    def test_wide_rect_top_and_bottom_rows(self):
        m = make_model(6, 5)
        cells = set(m.rect_outline(0, 0, 5, 2))
        # Top and bottom row must be fully present
        for x in range(6):
            assert (x, 0) in cells
            assert (x, 2) in cells


# ---------------------------------------------------------------------------
# midpoint_circle
# ---------------------------------------------------------------------------

class TestMidpointCircle:
    def test_radius_zero_returns_center(self):
        m = make_model(5, 5)
        cells = m.midpoint_circle(2, 2, 0)
        assert (2, 2) in cells

    def test_radius_zero_out_of_bounds_returns_empty(self):
        m = make_model(5, 5)
        assert m.midpoint_circle(10, 10, 0) == []

    def test_radius_one_has_cardinal_points(self):
        m = make_model(10, 10)
        cells = set(m.midpoint_circle(5, 5, 1))
        assert (6, 5) in cells  # right
        assert (4, 5) in cells  # left
        assert (5, 6) in cells  # below
        assert (5, 4) in cells  # above

    def test_clips_out_of_bounds(self):
        m = make_model(5, 5)
        cells = m.midpoint_circle(0, 0, 3)
        for x, y in cells:
            assert m.in_bounds(x, y)

    def test_no_duplicate_cells(self):
        m = make_model(20, 20)
        cells = m.midpoint_circle(10, 10, 5)
        assert len(cells) == len(set(cells))

    def test_8_way_symmetry(self):
        m = make_model(20, 20)
        cells = set(m.midpoint_circle(10, 10, 4))
        cx, cy = 10, 10
        for x, y in list(cells):
            dx, dy = x - cx, y - cy
            assert (cx - dx, cy + dy) in cells
            assert (cx + dx, cy - dy) in cells
            assert (cx - dx, cy - dy) in cells

    def test_negative_radius_returns_center(self):
        m = make_model(5, 5)
        # r <= 0 falls back to center point
        cells = m.midpoint_circle(2, 2, -1)
        assert (2, 2) in cells
