from django.db.models import Prefetch
from django.db.models.constants import LOOKUP_SEP


class SerializerPrefetch(Prefetch):
    """
    Class which functions the same as a Prefetch only this class allows to add a prefix,
    friendly for using with QuerySetSerializer
    """
    def __init__(self, lookup, queryset=None, to_attr=None, prefix=None):
        super().__init__(lookup, queryset=queryset, to_attr=to_attr)
        if prefix:
            self.apply_prefix(prefix, to_attr)

    def apply_prefix(self, prefix, to_attr=None):
        """
        Will apply the prefix supplied to all relations in the self.prefetch_trough
        Example:
            prefix = 'P_',  to_attr='attr',     lookup='a__b__c__d__e' ->
                            to_attr: P_attr,    prefetch_to='P_a__P_b__P_c__P_d__P_attr

            prefix = 'P_',  to_attr=None,       lookup='a__b__c__d__e' ->
                            to_attr='P_e'       prefetch_to='P_a__P_b__P_c__P_d__P_e

            prefix = 'P_',  to_attr=None,       lookup='a' ->
                            to_attr='P_a'       prefetch_to='P_a'

            prefix = 'P_',  to_attr='attr',     lookup='a' ->
                            to_attr='P_attr'    prefetch_to='P_attr'

        if no prefix is supplied it will go back to Prefetch its default behaviour
        :param prefix: str
        :param to_attr: str
        :return:
        """

        # set the value to_attr or the last key of self.prefetch_through
        to_attr = to_attr or self.prefetch_through.split(LOOKUP_SEP)[-1]
        # combine every key expect the last of self.prefetch_through and apply the prefix, add the to_attr as last key
        self.prefetch_to = LOOKUP_SEP.join(
            [prefix + trough for trough in self.prefetch_through.split(LOOKUP_SEP)[:-1]] + [prefix + to_attr]
        )
        self.to_attr = prefix + to_attr
