from telethon import types, custom
from telethon.utils import get_peer_id
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def replyHandler(message: custom.message.Message, users: set[int]) -> str | int:
    # check if this message is a reply to another
    try:
        if not message or not message.reply_to:
            return 0

        # check if it's from a user or a channel
        repliedTo = message.reply_to

        # temp solution unitl I make some stuff for stories
        if isinstance(repliedTo, types.MessageReplyStoryHeader):
            return "Replied to a story"

        if not (repliedTo and repliedTo.reply_to_peer_id):
            # This case is for replies from private dialogs
            if not message.reply_to_msg_id:
                return f"{message.reply_to.reply_from.from_name}:{message.reply_to.quote_text}"

            return message.reply_to_msg_id

        # if it's from a channel
        repliedToID = get_peer_id(repliedTo.reply_to_peer_id)

        if repliedToID not in users:
            users.add(repliedToID)

        return f"{repliedToID}:{message.reply_to_msg_id}"

    except Exception as e:
        logger.exception(f"Exception occurred : {e}")

    return 0


def forwardHandler(message: custom.message.Message, users: set[int]) -> list[str | int]:
    try:
        if not message or not message.forward:
            return [0, 0]

        forward = message.forward

        forwardFromName = f"{forward.from_name}"
        if not forward.from_id:
            return [forwardFromName, 0]

        entity = forward.from_id
        peerId = get_peer_id(entity)

        if peerId not in users:
            users.add(peerId)

        return [forwardFromName, peerId]
    except Exception as e:
        logger.exception(f"Exception occurred : {e}")

    return [0, 0]


def textHandler(message: custom.message.Message) -> str:
    # check for text
    text = ""
    if message.text:
        text = f"{message.text}"
    elif isinstance(message, types.MessageService):
        action = message.action
        if isinstance(action, types.MessageActionPinMessage):
            text = f"a message was pinned"
        elif isinstance(action, types.MessageActionChatAddUser):
            text = f"{action.users} was added"
        elif isinstance(action, types.MessageActionChatJoinedByLink):
            text = f"{action.inviter_id} joined"
        elif isinstance(action, types.MessageActionChatDeleteUser):
            text = f"{action.user_id} was kicked/left"
        elif isinstance(action, types.MessageActionChatEditPhoto):
            text = f"chat photo changed"
        elif isinstance(action, types.MessageActionChatEditTitle):
            text = f"chat title changed to {action.title}"
        elif isinstance(action, types.MessageActionChatCreate):
            text = f"{action.title} was created with users: {action.users}"
        else:
            text = f"{action} was done."

    return text


"""
Available message action:

MessageActionBoostApply
MessageActionBotAllowed
MessageActionChangeCreator
MessageActionChannelCreate
MessageActionChannelMigrateFrom
MessageActionChatAddUser
MessageActionChatCreate
MessageActionChatDeletePhoto
MessageActionChatDeleteUser
MessageActionChatEditPhoto
MessageActionChatEditTitle
MessageActionChatJoinedByLink
MessageActionChatJoinedByRequest
MessageActionChatMigrateTo
MessageActionConferenceCall
MessageActionContactSignUp
MessageActionCustomAction
MessageActionEmpty
MessageActionGameScore
MessageActionGeoProximityReached
MessageActionGiftCode
MessageActionGiftPremium
MessageActionGiftStars
MessageActionGiftTon
MessageActionGiveawayLaunch
MessageActionGiveawayResults
MessageActionGroupCall
MessageActionGroupCallScheduled
MessageActionHistoryClear
MessageActionInviteToGroupCall
MessageActionManagedBotCreated
MessageActionNewCreatorPending
MessageActionNoForwardsRequest
MessageActionNoForwardsToggle
MessageActionPaidMessagesPrice
MessageActionPaidMessagesRefunded
MessageActionPaymentRefunded
MessageActionPaymentSent
MessageActionPaymentSentMe
MessageActionPhoneCall
MessageActionPinMessage
MessageActionPollAppendAnswer
MessageActionPollDeleteAnswer
MessageActionPrizeStars
MessageActionRequestedPeer
MessageActionRequestedPeerSentMe
MessageActionScreenshotTaken
MessageActionSecureValuesSent
MessageActionSecureValuesSentMe
MessageActionSetChatTheme
MessageActionSetChatWallPaper
MessageActionSetMessagesTTL
MessageActionStarGift
MessageActionStarGiftPurchaseOffer
MessageActionStarGiftPurchaseOfferDeclined
MessageActionStarGiftUnique
MessageActionSuggestBirthday
MessageActionSuggestProfilePhoto
MessageActionSuggestedPostApproval
MessageActionSuggestedPostRefund
MessageActionSuggestedPostSuccess
MessageActionTodoAppendTasks
MessageActionTodoCompletions
MessageActionTopicCreate
MessageActionTopicEdit
MessageActionWebViewDataSent
MessageActionWebViewDataSentMe


Todo Actions:

MessageActionChannelCreate
MessageActionChannelMigrateFrom
MessageActionChatAddUser
MessageActionChatCreate
MessageActionChatDeletePhoto
MessageActionChatDeleteUser
MessageActionChatEditPhoto
MessageActionChatEditTitle
MessageActionChatJoinedByLink
MessageActionChatJoinedByRequest
MessageActionChatMigrateTo
MessageActionConferenceCall
MessageActionGroupCall
MessageActionGroupCallScheduled
MessageActionHistoryClear
MessageActionInviteToGroupCall
MessageActionPhoneCall
MessageActionPinMessage
MessageActionSetChatTheme
MessageActionSetChatWallPaper
MessageActionTopicEdit

"""
