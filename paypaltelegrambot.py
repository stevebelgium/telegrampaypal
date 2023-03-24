import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
import paypalrestsdk

# Define constants for PayPal configuration
PAYPAL_MODE = 'sandbox' # 'live' if using real PayPal account
PAYPAL_CLIENT_ID = credentials.paypal_client_id
PAYPAL_CLIENT_SECRET = credentials.paypal_client_secret

# Initialize PayPal SDK
paypalrestsdk.configure({
  'mode': PAYPAL_MODE,
  'client_id': "<<your_paypal_client_id>>",
  'client_secret': "<<your_paypal_client_secret>>"
})

# Define conversation states
PAYMENT_AMOUNT, PAYMENT_CONFIRMATION = range(2)

# Define command handler for /start command
def start(update, context):
	context.bot.send_message(chat_id=update.effective_chat.id, text='Welcome to my bot! Use /buy to purchase something.')

# Define command handler for /buy command
def buy_button_amount(update, context):
	# Ask user for payment amount
	keyboard = [
        [InlineKeyboardButton("$50", callback_data='40')],
        [
            InlineKeyboardButton("$40", callback_data='40'),
            InlineKeyboardButton("$30", callback_data='30'),
        ],
        [InlineKeyboardButton("$20", callback_data='20')],
        [InlineKeyboardButton("cancel", callback_data='0')],
    ]
	reply_markup = InlineKeyboardMarkup(keyboard)
	context.bot.send_message(chat_id=update.effective_chat.id, text=f'How much do you want to pay?', reply_markup=reply_markup)

	# Transition to ask_for_confirmation
	return PAYMENT_AMOUNT

# Define command handler for /buy_manual_amount command
def buy_manual_amount(update, context):
	# Ask user for payment amount
    context.bot.send_message(chat_id=update.effective_chat.id, text='How much do you want to pay?')

    # Transition to ask_for_confirmation
    return PAYMENT_AMOUNT

# Define message handler for ask_for_confirmation
def ask_for_confirmation(update, context):
	# Store payment amount in user data
	if update.message is None:
		# Handle /buy_manual_amount response
		context.user_data['payment_amount'] = update.callback_query.data
		query = update.callback_query.data
	else:
		# Handle buy reponse
		context.user_data['payment_amount'] = update.message.text
		query = update.message.text
	
	if query != "0":
		# Ask user for confirmation
		keyboard = [[InlineKeyboardButton("Yes", callback_data='yes'), InlineKeyboardButton("No", callback_data='no')]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		context.bot.send_message(chat_id=update.effective_chat.id, text=f'You want to pay {query}?', reply_markup=reply_markup)
	else:
		# Payment is cancelled when amount is 0
		context.bot.send_message(chat_id=update.effective_chat.id, text='Payment cancelled.')
		# End conversation
		return ConversationHandler.END


	# Transition to payment_confirmation
	return PAYMENT_CONFIRMATION

# Define callback query handler for payment confirmation
def payment_confirmation(update, context):
	# Handle YES/NO response
	query = update.callback_query
	if query.data == 'yes':
		# Create PayPal payment object
		payment = paypalrestsdk.Payment({
		  "intent": "sale",
		  "payer": {
			"payment_method": "paypal"
		  },
		  "transactions": [{
			"amount": {
			  "total": context.user_data['payment_amount'],
			  "currency": "USD"
			},
			"description": "Payment for my bot"
		  }],
		  "redirect_urls": {
			"return_url": "http://example.com/your_redirect_url",
			"cancel_url": "http://example.com/your_cancel_url"
		  }
		})
		
		# Create PayPal payment and get approval URL
		if payment.create():
			for link in payment.links:
				if link.rel == 'approval_url':
					approval_url = link.href
					context.user_data['paypal_payment_id'] = payment.id
					break
			else:
				# Payment creation failed
				context.bot.send_message(chat_id=update.effective_chat.id, text='Payment creation failed.')
				return ConversationHandler.END
		else:
			# Payment creation failed
			context.bot.send_message(chat_id=update.effective_chat.id, text='Payment creation failed.')
			return ConversationHandler.END
		
		# Send approval URL to user
		context.bot.send_message(chat_id=update.effective_chat.id, text=f'Please click the following link to complete the payment:\n{approval_url}')
		
	elif query.data == 'no':
		context.bot.send_message(chat_id=update.effective_chat.id, text='Payment cancelled.')
	
	# End conversation
	return ConversationHandler.END

def cancel(update, context):
    """Cancel the current operation and end the conversation"""
    update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
	"""Main function to start the bot and handle commands"""
	
	# Create the Updater and pass it your bot's token.
	updater = Updater("<<your_telegram_api_key>>")

	# Get the dispatcher to register handlers
	dispatcher = updater.dispatcher

	# Define command handlers
	buy_button_amount_handler = CommandHandler('buy_button_amount', buy_button_amount)
	buy_manual_amount_handler = CommandHandler('buy_manual_amount', buy_manual_amount)
	
	# Add conversation_handler for manual input
	conversation_handler_manual = ConversationHandler(
		entry_points=[buy_button_amount_handler],
		states={
			PAYMENT_AMOUNT: [CallbackQueryHandler(ask_for_confirmation)],
        	PAYMENT_CONFIRMATION: [CallbackQueryHandler(payment_confirmation)]
    },
		fallbacks=[CommandHandler('cancel', cancel)]
	)
	dispatcher.add_handler(conversation_handler_manual)

	# Add conversation_handler for button input
	conversation_handler_buttons = ConversationHandler(
		entry_points=[buy_manual_amount_handler],
		states={
			PAYMENT_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, ask_for_confirmation)],
        	PAYMENT_CONFIRMATION: [CallbackQueryHandler(payment_confirmation)]
    },
		fallbacks=[CommandHandler('cancel', cancel)]
	)
	dispatcher.add_handler(conversation_handler_buttons)

	# Define command handlers
	start_handler = CommandHandler('start', start)
	cancel_handler = CommandHandler('cancel', cancel)
	
	# Add command handlers to dispatcher
	dispatcher.add_handler(start_handler)
	dispatcher.add_handler(cancel_handler)
	
	# Start the Bot
	updater.start_polling()

	# Run the bot until you press Ctrl-C or the process receives SIGINT,
	# SIGTERM or SIGABRT. This should be used most of the time, since
	# start_polling() is non-blocking and will stop the bot gracefully.
	updater.idle()


if __name__ == '__main__':
	main()

