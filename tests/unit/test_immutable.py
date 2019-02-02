"""Test immutability helpers."""

import pytest

from pypiserver.immutable import (
    Freezable,
    FrozenAssignmentError,
    Immutable,
    ImmutableAssignmentError,
    ImmutableInstantiationError,
    ImmutableStatic,
)


# pylint: disable=no-self-use


class TestImmutableStatic:
    """Tests for the static immutable class."""

    @pytest.fixture()
    def empty_static(self):
        """Return a new ImmutableStatic child class with no attrs."""
        return type("ImmutableStaticChild", (ImmutableStatic,), {})

    def test_no_instantiation(self, empty_static):
        """Classes inheriting ImmutableStatic cannot be instantiated."""
        with pytest.raises(ImmutableInstantiationError):
            empty_static()

    def test_static_attrs_definable(self):
        """Static attributes may be defined on ImmutableStatics."""
        kls = type("A", (ImmutableStatic,), {"foo": "foo"})
        assert "foo" == kls.foo

    def test_new_attrs_not_definable_dot(self, empty_static):
        """New attributes may not be defined on ImmutableStatics."""
        with pytest.raises(ImmutableAssignmentError):
            empty_static.bar = "bar"

    def test_new_attrs_not_definable_setattr(self, empty_static):
        """New attributes may not be defined on ImmutableStatics."""
        with pytest.raises(ImmutableAssignmentError):
            setattr(empty_static, "bar", "bar")

    def test_attrs_not_reassignable_dot(self):
        """Existing attributes may not be reassigned on ImmutableStatics."""
        kls = type("A", (ImmutableStatic,), {"a": "a"})
        with pytest.raises(ImmutableAssignmentError):
            kls.a = "new_a"

    def test_attrs_not_reassignable_setattr(self):
        """Existing attributes may not be reassigned on ImmutableStatics."""
        kls = type("A", (ImmutableStatic,), {"a": "a"})
        with pytest.raises(ImmutableAssignmentError):
            setattr(kls, "a", "new_a")

    def test_staticmethods_definable(self):
        """Static methods are settable at definition time."""

        class Immut(ImmutableStatic):
            """Simple test class."""

            @staticmethod
            def get_a():
                """Return an a."""
                return "a"

        assert "a" == Immut.get_a()

    def test_regular_methods_definable(self):
        """Methods are settable at definition time.

        Note that this is fine for an ImmutableStatic, although it's
        probably still best practice to decorate with @staticmethod,
        b/c `self` is only passed into undecorated instance methods when
        accessed via an instance, and we can't have instances.
        """

        class Immut(ImmutableStatic):
            """Simple test class."""

            def get_a():  # pylint: disable=no-method-argument
                """Return an a."""
                return "a"

        assert "a" == Immut.get_a()

    def test_classmethods_definable(self):
        """Class methods are settable at definition time."""

        class Immut(ImmutableStatic):
            """Simple test class."""

            @classmethod
            def return_cls(cls):
                """Return an a."""
                return cls

        assert Immut is Immut.return_cls()

    def test_mutate_assigned_attr(self):
        """We can't do anything about mutating attribute values."""
        kls = type("A", (ImmutableStatic,), {"a": {}})
        assert {} == kls.a

        kls.a["b"] = "b"
        assert "b" == kls.a["b"]

    def test_immutability_affects_children(self, empty_static):
        """Child classes are also immutable."""
        child = type("B", (empty_static,), {})
        with pytest.raises(ImmutableAssignmentError):
            child.a = "a"

    def test_children_inherit_static_attrs(self):
        """Children inherit static attributes from their parents."""
        parent = type("A", (ImmutableStatic,), {"a": "a"})
        child = type("B", (parent,), {"b": "b"})

        assert "a" == parent.a == child.a
        assert "b" == child.b

    def test_cannot_override_instantiation_behavior(self):
        """Classes cannot override the default disallowed init."""
        kls = type("A", (ImmutableStatic,), {"__init__": lambda self: None})
        with pytest.raises(ImmutableInstantiationError):
            kls()


class TestImmutable:
    """Immutable classes may be instantiated, but not altered thereafter."""

    @pytest.fixture()
    def std_init(self):
        """Just an example init file that sets an instance variable."""

        def init_closure(inst):
            inst.a = "a"

        return init_closure

    @pytest.fixture()
    def empty_immut(self):
        """Return a new Immutable class with no attrs."""
        return type("ImmutableChild", (Immutable,), {})

    @pytest.fixture()
    def std_immut(self, std_init):
        """Return an Immutable child implementing the std_init."""
        return type("StdImmutableChild", (Immutable,), {"__init__": std_init})

    def test_instantiation_allowed(self, empty_immut):
        """Classes inheriting Immutable can be instantiated."""
        empty_immut()

    def test_static_attrs_definable(self):
        """Static attributes may be defined on Immutables."""
        kls = type("A", (Immutable,), {"foo": "foo"})
        assert "foo" == kls.foo

    def test_static_attrs_retained_on_instance(self):
        """Static attributes are accessible from Immutable instances."""
        kls = type("A", (Immutable,), {"foo": "foo"})
        assert "foo" == kls().foo

    def test_instance_attrs_definable(self, std_immut):
        """Instance attributes may be defined in init for Immutables."""
        assert "a" == std_immut().a

    def test_new_cls_attrs_not_definable_dot(self, empty_immut):
        """New attributes may not be defined on Immutable classes."""
        with pytest.raises(ImmutableAssignmentError):
            empty_immut.bar = "bar"

    def test_new_inst_attrs_not_definable_dot(self, empty_immut):
        """New attributes may not be defined on Immutable instances."""
        with pytest.raises(ImmutableAssignmentError):
            empty_immut().bar = "bar"

    def test_new_cls_attrs_not_definable_setattr(self, empty_immut):
        """New attributes may not be defined on Immutable classes."""
        with pytest.raises(ImmutableAssignmentError):
            setattr(empty_immut, "bar", "bar")

    def test_new_inst_attrs_not_definable_setattr(self, empty_immut):
        """New attributes may not be defined on Immutable instances."""
        with pytest.raises(ImmutableAssignmentError):
            setattr(empty_immut(), "bar", "bar")

    def test_inst_attrs_not_reassignable(self, std_immut):
        """Existing attributes may not be reassigned on ImmutableStatics."""
        with pytest.raises(ImmutableAssignmentError):
            std_immut().a = "new_a"

    def test_mutate_assigned_attr(self):
        """We can't do anything about mutating attribute values."""
        inst = type("A", (Immutable,), {"a": {}})()
        assert {} == inst.a

        inst.a["b"] = "b"
        assert "b" == inst.a["b"]

    def test_immutability_affects_children(self, empty_immut):
        """Child classes are also immutable."""
        child = type("B", (empty_immut,), {})()
        with pytest.raises(ImmutableAssignmentError):
            child.a = "a"

    def test_children_inherit_init_attrs(self, std_immut):
        """Children inherit static attributes from their parents."""
        child = type("B", (std_immut,), {"b": "b"})()

        assert "a" == child.a
        assert "b" == child.b

    def test_chained_inits(self, std_immut):
        """Children and parent init methods should work normally."""

        class _Child(std_immut):
            def __init__(self):
                super().__init__(delay_freeze=True)
                self.b = "b"

        child = _Child()

        assert "a" == child.a
        assert "b" == child.b

    def test_doubly_chained_inits(self, std_immut):
        """Grand-children's init methods also work as expected."""

        class _Child(std_immut):
            cls_b = "b"

            def __init__(self):
                super().__init__(delay_freeze=True)
                self.b = "b"

        class _GrandChild(_Child):
            cls_c = "c"

            def __init__(self):
                # pylint: disable=unexpected-keyword-arg
                super().__init__(delay_freeze=True)
                self.c = "c"

        grand_child = _GrandChild()

        assert "a" == grand_child.a
        assert "b" == grand_child.b == grand_child.cls_b
        assert "c" == grand_child.c == grand_child.cls_c


class TestFreezable:
    """Freezable classes may be made [im]mutable at will."""

    @pytest.fixture()
    def empty_freezable(self):
        """Return a new Freezable class with no attrs."""
        return type("FreezableChild", (Freezable,), {})

    def test_instantiation_allowed(self, empty_freezable):
        """Classes inheriting Freezable can be instantiated."""
        empty_freezable()

    def test_static_attrs_definable(self):
        """Static attributes may be defined on Freezables."""
        kls = type("A", (Freezable,), {"foo": "foo"})
        assert "foo" == kls.foo

    def test_static_attrs_retained_on_instance(self):
        """Static attributes are accessible from Freezable instances."""
        kls = type("A", (Freezable,), {"foo": "foo"})
        assert "foo" == kls().foo

    def test_class_attrs_definable(self, empty_freezable):
        """Class attributes should be definable."""
        empty_freezable.a = "a"
        assert "a" == empty_freezable.a

    def test_instance_attrs_definable_in_init(self):
        """Instance attributes may be defined in init for Freezables."""
        inst = type(
            "A", (Freezable,), {"__init__": lambda s: setattr(s, "a", "a")}
        )()
        assert "a" == inst.a  # pylint: disable=no-member

    def test_intstance_attrs_definable_post_init(self, empty_freezable):
        """Instance attributes may be defined on an unfrozen instance."""
        empty_freezable.b = "b"
        assert "b" == empty_freezable.b

    def test_instance_attrs_not_definable_once_frozen(self, empty_freezable):
        """Once frozen, instance attributes may not be set."""
        inst = empty_freezable()
        inst.freeze()
        with pytest.raises(FrozenAssignmentError):
            inst.a = "a"

    def test_instance_attrs_not_reassignable_once_frozen(
        self, empty_freezable
    ):
        """Once frozen, instance attributes may not be set."""
        inst = empty_freezable()
        inst.a = "a"
        inst.freeze()
        with pytest.raises(FrozenAssignmentError):
            inst.a = "b"
        assert "a" == inst.a

    def test_instance_attrs_not_reassignable_once_frozen_setattr(
        self, empty_freezable
    ):
        """Once frozen, instance attributes may not be set."""
        inst = empty_freezable()
        inst.a = "a"
        inst.freeze()
        with pytest.raises(FrozenAssignmentError):
            setattr(inst, "a", "b")
        assert "a" == inst.a

    def test_children_freezable(self, empty_freezable):
        """Child classes are also freezable."""
        child = type("B", (empty_freezable,), {})()
        child.b = "b"
        child.freeze()
        with pytest.raises(FrozenAssignmentError):
            child.b = "c"

    def test_parent_frozen_state_does_not_affect_child(self, empty_freezable):
        """The state of freeable children is independent from parents."""
        parent = empty_freezable()
        parent.a = "a"
        parent.freeze()
        child = type("B", (parent.__class__,), {})()
        assert not hasattr(child, "a")
        child.b = "b"
        child.freeze()
        with pytest.raises(FrozenAssignmentError):
            child.b = "c"
