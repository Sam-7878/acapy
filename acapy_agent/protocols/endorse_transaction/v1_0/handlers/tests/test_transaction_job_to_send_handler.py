from unittest import IsolatedAsyncioTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...handlers import transaction_job_to_send_handler as test_module
from ...messages.transaction_job_to_send import TransactionJobToSend


class TestTransactionJobToSendHandler(IsolatedAsyncioTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context(await create_test_profile())
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.set_transaction_their_job = mock.CoroutineMock()
            request_context.message = TransactionJobToSend()
            request_context.connection_ready = True
            handler = test_module.TransactionJobToSendHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_tran_mgr.return_value.set_transaction_their_job.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages

    async def test_called_x(self):
        request_context = RequestContext.test_context(await create_test_profile())
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        with mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_tran_mgr:
            mock_tran_mgr.return_value.set_transaction_their_job = mock.CoroutineMock(
                side_effect=test_module.TransactionManagerError()
            )
            request_context.message = TransactionJobToSend()
            request_context.connection_ready = True
            handler = test_module.TransactionJobToSendHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_tran_mgr.return_value.set_transaction_their_job.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages
