import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6 import QtCore

from anylabeling.views.labeling.label_widget import LabelingWidget
from tests.test_canvas.test_navigation import (  # noqa: F401
    NavigationView,
    image_position,
    navigation_app,
    view,
)

NavigationView.pinch_zoom_request = LabelingWidget.pinch_zoom_request


def pinch(view, factor, point):
    view.canvas.pinch_zoom_request.emit(
        factor, (point - QtCore.QPointF(view.canvas.pos())).toPoint()
    )


def assert_kept(actual, expected):
    assert actual.x() == pytest.approx(expected.x(), abs=0.5)
    assert actual.y() == pytest.approx(expected.y(), abs=0.5)


@pytest.fixture
def pinch_view(view):
    view.canvas.pinch_zoom_request.connect(view.pinch_zoom_request)
    return view


def test_pinch_zoom_does_not_drift_over_many_events(pinch_view):
    point = QtCore.QPointF(330, 90) + QtCore.QPointF(pinch_view.canvas.pos())
    before = image_position(pinch_view, point)

    for _ in range(60):
        pinch(pinch_view, 1.013, point)
    for _ in range(30):
        pinch(pinch_view, 0.99, point)

    assert pinch_view.canvas.scale > 1.5
    assert_kept(image_position(pinch_view, point), before)


def test_tiny_pinch_steps_are_not_swallowed_by_zoom_rounding(pinch_view):
    point = QtCore.QPointF(200, 150) + QtCore.QPointF(pinch_view.canvas.pos())
    for _ in range(100):
        pinch(pinch_view, 1.002, point)
    assert pinch_view.canvas.scale == pytest.approx(1.002**100)


def test_pinch_after_pan_anchors_on_new_point_under_cursor(pinch_view):
    point = QtCore.QPointF(200, 150) + QtCore.QPointF(pinch_view.canvas.pos())
    for _ in range(10):
        pinch(pinch_view, 1.02, point)

    # Trackpad pan: the image moves while the cursor stays put.
    pinch_view.pan_canvas(QtCore.QPointF(-120, -120))
    after_pan = image_position(pinch_view, point)

    pinch(pinch_view, 1.02, point)

    assert_kept(image_position(pinch_view, point), after_pan)
