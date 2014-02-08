"""
A :class:`~glue.core.subset_group.Subset Group` unites a group of
:class:`~glue.core.Subset` instances together with a consistent state,
label, and style.

While subsets are internally associated with particular datasets, it's
confusing for the user to juggle multiple similar or identical
subsets, applied to different datasets. Because of this, the GUI
manages SubsetGroups, and presents each group to the user as a single
entity. The individual subsets are held in-sync by the SubsetGroup.

Client code should *only* create Subset Groups via
DataCollection.new_subset_group. It should *not* call Data.add_subset
or Data.new_subset directly
"""
from . import Subset
from .subset import SubsetState
from .util import Pointer
from .hub import HubListener
from .visual import VisualAttributes, RED
from .message import (DataCollectionAddMessage,
                      DataCollectionDeleteMessage
                      )


class GroupedSubset(Subset):
    """
    A member of a SubsetGroup, whose internal representation
    is shared with other group members
    """
    subset_state = Pointer('group.subset_state')
    label = Pointer('group.label')

    def __init__(self, data, group):
        """
        :param data: :class:`~glue.core.data.Data` instance to bind to
        :param group: :class:`~glue.core.subset_group.SubsetGroup`
        """
        self.group = group
        self._style_override = None
        super(GroupedSubset, self).__init__(data, label=group.label,
                                            color=group.style.color,
                                            alpha=group.style.alpha)

    @property
    def verbose_label(self):
        return "%s (%s)" % (self.label, self.data.label)

    @property
    def style(self):
        return self._style_override or self.group.style

    @style.setter
    def style(self, value):
        self._style_override = value

    def clear_override_style(self):
        if self._style_override is not None:
            self._style_override = None
            self.broadcast('style')

    def __eq__(self, other):
        return other is self


class SubsetGroup(HubListener):
    def __init__(self, color=RED, alpha=0.5, label=None):
        """
        Create a new empty SubsetGroup

        Note: By convention, SubsetGroups should be created via
        DataCollection.new_subset.
        """
        self.subsets = []
        self.subset_state = SubsetState()
        self.label = label
        self._style = None

        self.style = VisualAttributes(parent=self)
        self.style.markersize *= 2.5
        self.style.color = color
        self.style.alpha = alpha

    def register(self, data):
        """
        Register to a :class:`~glue.core.DataCollection`

        This is called automatically by DataCollection.new_subset_grouop
        """
        self.register_to_hub(data.hub)

        #add to self, then register, so fully populated by first
        #broadcast

        for d in data:
            s = GroupedSubset(d, self)
            self.subsets.append(s)

        for d, s in zip(data, self.subsets):
            d.add_subset(s)

    def paste(self, other_subset):
        """paste subset state from other_subset onto self """
        state = other_subset.subset_state.copy()
        self.subset_state = state

    def _add_data(self, data):
        s = GroupedSubset(data, self)
        data.add_subset(s)
        self.subsets.append(s)

    def _remove_data(self, data):
        for s in list(self.subsets):
            if s.data is data:
                self.subsets.remove(s)

    def register_to_hub(self, hub):
        hub.subscribe(self, DataCollectionAddMessage,
                      lambda x: self._add_data(x.data))
        hub.subscribe(self, DataCollectionDeleteMessage,
                      lambda x: self._remove_data(x.data))

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        self._style = value
        self._clear_overrides()

    def _clear_overrides(self):
        for s in self.subsets:
            s.clear_override_style()

    def broadcast(self, item):
        #used by __setattr__ and VisualAttributes.__setattr__
        if isinstance(item, VisualAttributes):
            self._clear_overrides()
            return

        for s in self.subsets:
            s.broadcast(item)

    def __setattr__(self, attr, value):
        object.__setattr__(self, attr, value)
        if attr in ['subset_state', 'label', 'style']:
            self.broadcast(attr)
