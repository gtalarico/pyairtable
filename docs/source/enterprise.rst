.. include:: _substitutions.rst
.. include:: _warn_latest.rst


Enterprise Features
==============================


Retrieving information
----------------------

pyAirtable exposes a number of classes and methods for interacting with enterprise organizations.
The following methods are only available on an `Enterprise plan <https://airtable.com/pricing>`__.
If you call one of them against a base that is not part of an enterprise workspace, Airtable will
return a 404 error, and pyAirtable will add a reminder to the exception to check your billing plan.

.. automethod:: pyairtable.Api.enterprise
    :noindex:

.. automethod:: pyairtable.Base.collaborators
    :noindex:

.. automethod:: pyairtable.Base.shares
    :noindex:

.. automethod:: pyairtable.Workspace.collaborators
    :noindex:

.. automethod:: pyairtable.Enterprise.info
    :noindex:


Retrieving audit logs
---------------------

.. automethod:: pyairtable.Enterprise.audit_log
    :noindex:


Managing permissions and shares
-------------------------------

You can use pyAirtable to change permissions on a base or workspace
via the following methods exposed on schema objects.

If for some reason you need to call these API endpoints without first retrieving
schema information, you might consider calling :meth:`~pyairtable.Api.request` directly.

`Add base collaborator <https://airtable.com/developers/web/api/add-base-collaborator>`__

    >>> base.collaborators().add_user("usrUserId", "read")
    >>> base.collaborators().add_group("ugpGroupId", "edit")
    >>> base.collaborators().add("user", "usrUserId", "comment")

`Add interface collaborator <https://airtable.com/developers/web/api/add-interface-collaborator>`__

    >>> base.collaborators().interfaces[pbd].add_user("usrUserId", "read")
    >>> base.collaborators().interfaces[pbd].add_group("ugpGroupId", "read")
    >>> base.collaborators().interfaces[pbd].add("user", "usrUserId", "read")

`Add workspace collaborator <https://airtable.com/developers/web/api/add-workspace-collaborator>`__

    >>> workspace.collaborators().add_user("usrUserId", "read")
    >>> workspace.collaborators().add_group("ugpGroupId", "edit")
    >>> workspace.collaborators().add("user", "usrUserId", "comment")

`Update collaborator base permission <https://airtable.com/developers/web/api/update-collaborator-base-permission>`__

    >>> base.collaborators().update("usrUserId", "edit")
    >>> base.collaborators().update("ugpGroupId", "edit")

`Update interface collaborator <https://airtable.com/developers/web/api/update-interface-collaborator>`__

    >>> base.collaborators().interfaces[pbd].update("usrUserId", "edit")
    >>> base.collaborators().interfaces[pbd].update("ugpGroupId", "edit")

`Update workspace collaborator <https://airtable.com/developers/web/api/update-workspace-collaborator>`__

    >>> workspace.collaborators().update("usrUserId", "edit")
    >>> workspace.collaborators().update("ugpGroupId", "edit")

`Delete base collaborator <https://airtable.com/developers/web/api/delete-base-collaborator>`__

    >>> base.collaborators().remove("usrUserId")
    >>> base.collaborators().remove("ugpGroupId")

`Delete interface collaborator <https://airtable.com/developers/web/api/delete-interface-collaborator>`__

    >>> base.collaborators().interfaces[pbd].remove("usrUserId")
    >>> base.collaborators().interfaces[pbd].remove("ugpGroupId")

`Delete workspace collaborator <https://airtable.com/developers/web/api/delete-workspace-collaborator>`__

    >>> workspace.collaborators().remove("usrUserId")
    >>> workspace.collaborators().remove("ugpGroupId")

`Delete base invite <https://airtable.com/developers/web/api/delete-base-invite>`__

    >>> base.collaborators().invite_links.via_base[0].delete()
    >>> workspace.collaborators().invite_links.via_base[0].delete()

`Delete interface invite <https://airtable.com/developers/web/api/delete-interface-invite>`__

    >>> base.collaborators().interfaces[pbd].invite_links[0].delete()

`Delete workspace invite <https://airtable.com/developers/web/api/delete-workspace-invite>`__

    >>> base.collaborators().invite_links.via_workspace[0].delete()
    >>> workspace.collaborators().invite_links.via_workspace[0].delete()

`Manage share <https://airtable.com/developers/web/api/manage-share>`__

    >>> share = base.shares()[0]
    >>> share.disable()
    >>> share.enable()

`Delete share <https://airtable.com/developers/web/api/delete-share>`__

    >>> share.delete()

`Update workspace restrictions <https://airtable.com/developers/web/api/update-workspace-restrictions>`__

    >>> r = workspace.collaborators().restrictions
    >>> r.invite_creation = "unrestricted"
    >>> r.share_creation = "onlyOwners"
    >>> r.save()


Managing users
-------------------

You can use pyAirtable to manage an enterprise's users
via the following methods.

`Manage user <https://airtable.com/developers/web/api/manage-user>`__

    >>> user = enterprise.user("usrUserId")
    >>> user.state = "deactivated"
    >>> user.email = user.email.replace("@", "+deactivated@")
    >>> user.save()

`Logout user <https://airtable.com/developers/web/api/logout-user>`__

    >>> user.logout()

`Delete user by id <https://airtable.com/developers/web/api/delete-user-by-id>`__

    >>> user.delete()

`Remove user from enterprise <https://airtable.com/developers/web/api/remove-user-from-enterprise>`__

    >>> enterprise.remove_user("usrUserId", replacement="usrOtherUserId")

`Manage user membership <https://airtable.com/developers/web/api/manage-user-membership>`__

    >>> enterprise.claim_users({"userId": "managed"})

`Delete users by email <https://airtable.com/developers/web/api/delete-users-by-email>`__

    >>> enterprise.delete_users(["foo@example.com", "bar@example.com"])
