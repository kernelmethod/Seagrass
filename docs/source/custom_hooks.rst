.. _custom-hooks:

=====================
Creating custom hooks
=====================

Custom Seagrass event hooks must satisfy the ``ProtoHook`` interface in order to
be used to hook an audited event. Additionally, the event hook must also satisfy
the ``LoggableHook`` interface for the hook's results to be logged when you call
``auditor.log_results()``.


