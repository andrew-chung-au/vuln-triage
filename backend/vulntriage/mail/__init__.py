"""Owner-notification mail delivery (task 37).

The backend sends the top-tier owner notification itself (decision H7). This
package has:

- ``settings``: the mail-transport selection and the verified sender address,
  read from the environment at call time (the backend's per-module pattern).
- ``message``: the plain-text labelled-field formatter, with email-header
  CR/LF rejection and advisory-text URL defanging (A31, § Security boundaries).
- ``transport``: the ``MailTransport`` interface and its implementations — the
  in-process recording sink (``make test``), MailHog over SMTP
  (``make test-compose`` and local dev) and Amazon SES on AWS (VERIFY-marked,
  not exercised in CI). Each refuses a send from any address other than the
  configured verified sender.
- ``delivery``: the ``DeliveryWorker`` that claims a pending ``top tier`` job,
  formats and sends the message, records ``notification.deliver`` as a child of
  the job's stored ``traceparent``, and marks the job ``sent``/``failed``/held.
"""
