START TRANSACTION;

insert ignore into `market` (`name`, `spider`) values 
	('Dream Market', 'dreammarket'),
	('Hansa market', 'hansa_market'),
	( 'Traderoute Market', 'traderoute_market'),
	('Wallstreet Market', 'wallstreet_market'),
	('Darknet Heroes League Market', 'dhl_market'),
	('Cannabis Growers & Merchants Coop', 'cgmc_market'),
	('Libertas Market', 'libertas_market');

insert ignore into `ads_propkey` (`name`, `prettyname`) values 
	('price', 'Price'),
	('ships_to', 'Ships to'),
	('ships_from', 'Ships from'),
	('escrow', 'Escrow'),
	('description', 'Description'),
	('category', 'Category'),
	('shipping_options', 'Shipping Options'),
	('ships_to_except', 'Ships To Exceptions'),
	('ads_class', 'Class'),
	('in_stock', 'In Stock'),
	('terms_and_conditions', 'Terms & Condition'),
	('stock', 'Stock'),
	('price_options', 'Price Options'),
	('multilisting', 'Multilisting'),
	('multisig', 'Multisignature Available'),
	('views', 'Number of views'),
	('minimum_order', 'Minimum per order'),
	('maximum_order', 'Maximum per order'),
	('already_sold', 'Qty Already Sold'),
	('country', 'Country'),
	('replace_time', 'Replace Time'),
	('auto_accept', 'Auto Accept'),
    ('price_usd', 'Price (USD)'),
	('price_ltc', 'Price (litecoin)'),
    ('price_bch', 'Price (bitcoin cash)'),
    ('price_xmr', 'Price (monero)'),
	('accepted_currencies', 'Accepted Currencies');

insert ignore into `user_propkey` (`name`, `prettyname`) values 
	('successful_transactions', 'Successful Transactions'),
	('average_rating', 'Average Rating'),
	('agora_rating', 'Agora rating'),
	('nucleus_rating', 'Nucleus rating'),
	('alphabay_rating', 'Alphabay rating'),
	('abraxas_rating', 'Abraxas rating'),
	('midlle_earth_rating', 'Middle Earth rating'),
	('hansa_rating', 'Hansa rating'),
	('trusted_seller', 'Trusted seller'),
	('verified','Verified'),
	('fe_enabled', 'Finalize Early'),
	('join_date', 'Join date'),
	('last_active', 'Last active'),
	('terms_and_conditions', 'Terms and Conditions'),
	('public_pgp_key', 'Public PGP Key'),
	('dreammarket_rating', 'Dream Market Rating'),
	('valhalla_rating', 'Valhalla Rating'),
	('subscribers', 'Subscribers'),
	('positive_feedback', 'Positive Feedback'),
	('neutral_feedback', 'Neutral Feedback'),
	('negative_feedback', 'Negative Feedback'),
	('level', 'Level'),
	('avg_volume', 'Average volume'),
	('profile', 'Profile'),
	('oasis_rating', 'Oasis Rating'),
	('ship_to', 'Shipping To'),
	('ship_from', 'Shipping From'),
	('title', 'Title'),
	('exp', 'Exp'),
	('news', 'News Feed'),
	('successful_transactions_as_buyer', 'Successful Transaction As Buyer'),
	('shipping_information', 'Shipping Information'),
	('forum_posts', 'Forum Posts'),
	('feedback_received', 'Feedback Received'),
	('refund_policy', 'Refund Policy'),
	('reship_policy', 'Reshipping Policy');

insert ignore into `ads_feedback_propkey` (`name`, `prettyname`) values 
	('submitted_on', 'Submitted on'),
	('rating', 'Rating'),
	('comment', 'Comment'),
	('submitted_by','Submitted By'),
	('delivery_time', 'Delivery Time');

insert ignore into `seller_feedback_propkey` (`name`, `prettyname`) values 
	('submitted_on', 'Submitted on'),
	('rating', 'Rating'),
	('comment', 'Comment'),
	('submitted_by','Submitted By'),
	('delivery_time', 'Delivery Time'),
	('communication', 'Communication'),
	('speed', 'Delivery Speed'),
	('stealth', 'Stealth'),
	('quality', 'Quality'),
	('payment_type', 'Payment type'),
	('item_name', 'Item name'),
	('submitter_level', 'Submitter reputation level'),
	('price', 'Price');

COMMIT;