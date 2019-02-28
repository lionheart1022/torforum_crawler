-- MySQL dump 10.16  Distrib 10.1.19-MariaDB, for CYGWIN (x86_64)
--
-- Host: 127.0.0.1    Database: 127.0.0.1
-- ------------------------------------------------------
-- Server version	5.7.14

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ads`
--

DROP TABLE IF EXISTS `ads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `external_id` varchar(150) DEFAULT NULL,
  `market` bigint(11) NOT NULL,
  `title` text NOT NULL,
  `seller` bigint(11) DEFAULT NULL,
  `relativeurl` text,
  `fullurl` text,
  `last_update` timestamp NULL DEFAULT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_market_externalid` (`market`,`external_id`) USING BTREE,
  KEY `ads_market_idx` (`market`),
  KEY `ads_author_idx` (`seller`),
  KEY `ads_scrape_idx` (`scrape`),
  CONSTRAINT `ads_market` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_seller` FOREIGN KEY (`seller`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER ads_before_update_audit 
    BEFORE UPDATE ON ads
    FOR EACH ROW 
BEGIN
	IF OLD.scrape is not null
	THEN  
		SET NEW.scrape = OLD.scrape;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `ads_feedback`
--

DROP TABLE IF EXISTS `ads_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_feedback` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `market` bigint(11) NOT NULL,
  `ads` bigint(11) DEFAULT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  `hash` varchar(64) CHARACTER SET ascii DEFAULT NULL,
  `count` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ads_feedback_ads_hash_unique` (`ads`,`hash`),
  KEY `ads_feedback_market_idx` (`market`),
  KEY `ads_feedback_ads_idx` (`ads`),
  KEY `ads_feedback_scrape_idx` (`scrape`),
  KEY `ads_feedback_hash_idx` (`hash`),
  CONSTRAINT `ads_feedback_ads` FOREIGN KEY (`ads`) REFERENCES `ads` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_market` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ads_feedback_propkey`
--

DROP TABLE IF EXISTS `ads_feedback_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_feedback_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `prettyname` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ads_feedback_propval`
--

DROP TABLE IF EXISTS `ads_feedback_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_feedback_propval` (
  `propkey` bigint(11) NOT NULL,
  `feedback` bigint(11) NOT NULL,
  `data` mediumtext CHARACTER SET utf8mb4,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  PRIMARY KEY (`propkey`,`feedback`),
  KEY `ads_feedback_propval_feedback_idx` (`feedback`),
  KEY `ads_feedback_propval_feedbackkey_index` (`feedback`,`propkey`),
  KEY `ads_feedback_propval_modifiedon_index` (`modified_on`),
  KEY `ads_feedback_propval_scrape_idx` (`scrape`),
  CONSTRAINT `ads_feedback_propkey_key` FOREIGN KEY (`propkey`) REFERENCES `ads_feedback_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_propval_feedback` FOREIGN KEY (`feedback`) REFERENCES `ads_feedback` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_propval_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER ads_feedback_propval_before_update_audit 
    BEFORE UPDATE ON ads_feedback_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `ads_feedback_propvalaudit`
			(`modified_on`, `feedback`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`feedback`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	ELSE
		IF OLD.`scrape` is not null
        THEN
			SET NEW.`scrape` = OLD.`scrape`;
		END IF;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `ads_feedback_propvalaudit`
--

DROP TABLE IF EXISTS `ads_feedback_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_feedback_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `feedback` bigint(11) NOT NULL,
  `data` mediumtext CHARACTER SET utf8mb4,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) NOT NULL,
  KEY `ads_feedback_propvalaudit_feedback_idx` (`feedback`),
  KEY `ads_feedback_propvalaudit_propkey_idx` (`propkey`),
  KEY `ads_feedback_propvalaudit_feedbackkey_index` (`feedback`,`propkey`),
  KEY `ads_feedback_propvalaudit_modifiedon_index` (`modified_on`),
  KEY `ads_feedback_propvalaudit_scrape_idx` (`scrape`),
  CONSTRAINT `ads_feedback_propvalaudit_feedback` FOREIGN KEY (`feedback`) REFERENCES `ads_feedback` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_propvalaudit_propkey` FOREIGN KEY (`propkey`) REFERENCES `ads_feedback_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_feedback_propvalaudit_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ads_img`
--

DROP TABLE IF EXISTS `ads_img`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_img` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ads` bigint(11) NOT NULL,
  `path` varchar(255) NOT NULL,
  `hash` varchar(128) DEFAULT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ads_img_path_hash` (`hash`),
  KEY `adsimage_ads_fk_idx` (`ads`),
  KEY `ads_img_scrape_idx` (`scrape`),
  CONSTRAINT `ads_img_ads` FOREIGN KEY (`ads`) REFERENCES `ads` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_img_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER ads_image_before_update_audit 
    BEFORE UPDATE ON ads_img
    FOR EACH ROW 
BEGIN
	IF OLD.`scrape` is not null
	THEN  
		SET NEW.scrape = OLD.scrape;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `ads_propkey`
--

DROP TABLE IF EXISTS `ads_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `prettyname` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ads_propval`
--

DROP TABLE IF EXISTS `ads_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_propval` (
  `propkey` bigint(11) NOT NULL,
  `ads` bigint(11) NOT NULL,
  `data` mediumtext,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  PRIMARY KEY (`propkey`,`ads`),
  KEY `ads_propval_ads_idx` (`ads`),
  KEY `ads_propval_adskey_index` (`ads`,`propkey`),
  KEY `ads_propval_modifiedon_index` (`modified_on`),
  KEY `ads_propval_scrape_idx` (`scrape`),
  CONSTRAINT `ads_propkey_key` FOREIGN KEY (`propkey`) REFERENCES `ads_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_propval_ads` FOREIGN KEY (`ads`) REFERENCES `ads` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_propval_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER ads_propval_before_update_audit 
    BEFORE UPDATE ON ads_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `ads_propvalaudit`
			(`modified_on`, `ads`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`ads`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	ELSE 
		IF OLD.`scrape` is not null
		THEN  
			SET NEW.scrape = OLD.scrape;
		END IF;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `ads_propvalaudit`
--

DROP TABLE IF EXISTS `ads_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ads_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `ads` bigint(11) NOT NULL,
  `data` mediumtext,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) NOT NULL,
  KEY `ads_propvalaudit_ads_idx` (`ads`),
  KEY `ads_propvalaudit_propkey_idx` (`propkey`),
  KEY `ads_propvalaudit_adskey_index` (`ads`,`propkey`),
  KEY `ads_propvalaudit_modifiedon_index` (`modified_on`),
  KEY `ads_propvalaudit_scrape_idx` (`scrape`),
  CONSTRAINT `ads_propvalaudit_propkey` FOREIGN KEY (`propkey`) REFERENCES `ads_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_propvalaudit_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ads_propvalaudit_user` FOREIGN KEY (`ads`) REFERENCES `ads` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `captcha_question`
--

DROP TABLE IF EXISTS `captcha_question`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `captcha_question` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `market` bigint(11) NOT NULL,
  `hash` varchar(64) CHARACTER SET ascii NOT NULL,
  `question` text,
  `answer` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `hash_UNIQUE` (`market`,`hash`),
  KEY `question_market_idx` (`market`),
  CONSTRAINT `question_market` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `changerate`
--

DROP TABLE IF EXISTS `changerate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `changerate` (
  `time` timestamp NOT NULL,
  `btc` float NOT NULL,
  `usd` float DEFAULT NULL,
  PRIMARY KEY (`time`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `manual_input`
--

DROP TABLE IF EXISTS `manual_input`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `manual_input` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `date_requested` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `spidername` varchar(255) COLLATE utf8mb4_bin NOT NULL,
  `proxy` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL,
  `login` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL,
  `login_info` text COLLATE utf8mb4_bin,
  `cookies` text COLLATE utf8mb4_bin,
  `user_agent` text COLLATE utf8mb4_bin,
  `reload` tinyint(4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `market`
--

DROP TABLE IF EXISTS `market`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `market` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `spider` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`),
  UNIQUE KEY `spider_UNIQUE` (`spider`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `process`
--

DROP TABLE IF EXISTS `process`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `process` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `start` timestamp NULL DEFAULT NULL,
  `end` timestamp NULL DEFAULT NULL,
  `pid` int(11) DEFAULT NULL,
  `cmdline` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scrape`
--

DROP TABLE IF EXISTS `scrape`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `scrape` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `process` bigint(11) NOT NULL,
  `market` bigint(11) DEFAULT NULL,
  `start` timestamp NULL DEFAULT NULL,
  `end` timestamp NULL DEFAULT NULL,
  `reason` text,
  `login` varchar(255) DEFAULT NULL,
  `proxy` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scrape_market_fk_idx` (`market`),
  KEY `scrape_process_fk_idx` (`process`),
  KEY `scrape_processmarket_idx` (`process`,`market`),
  CONSTRAINT `scrape_market_fk` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `scrape_process_fk` FOREIGN KEY (`process`) REFERENCES `process` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scrapestat`
--

DROP TABLE IF EXISTS `scrapestat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `scrapestat` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `scrape` bigint(11) NOT NULL,
  `logtime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `ram_usage` bigint(20) DEFAULT NULL,
  `request_sent` bigint(20) DEFAULT NULL,
  `request_bytes` bigint(20) DEFAULT NULL,
  `response_received` bigint(20) DEFAULT NULL,
  `response_bytes` bigint(20) DEFAULT NULL,
  `item_scraped` bigint(20) DEFAULT NULL,
  `item_dropped` bigint(20) DEFAULT NULL,
  `ads` bigint(20) DEFAULT NULL,
  `ads_propval` bigint(20) DEFAULT NULL,
  `ads_feedback` bigint(20) DEFAULT NULL,
  `ads_feedback_propval` bigint(20) DEFAULT NULL,
  `user` bigint(20) DEFAULT NULL,
  `user_propval` bigint(20) DEFAULT NULL,
  `seller_feedback` bigint(20) DEFAULT NULL,
  `seller_feedback_propval` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scrapestat_scrape_fk_idx` (`scrape`),
  KEY `scrapestat_scrapetime_idx` (`scrape`,`logtime`),
  CONSTRAINT `scrapestat_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `seller_feedback`
--

DROP TABLE IF EXISTS `seller_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `seller_feedback` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `market` bigint(11) NOT NULL,
  `seller` bigint(11) DEFAULT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  `hash` varchar(64) CHARACTER SET ascii DEFAULT NULL,
  `count` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `seller_feedback_seller_hash_unique` (`seller`,`hash`),
  KEY `seller_feedback_market_idx` (`market`),
  KEY `seller_feedback_author_idx` (`seller`),
  KEY `seller_feeddback_scrape_idx` (`scrape`),
  KEY `seller_feedback_hash_idx` (`hash`),
  CONSTRAINT `seller_feedback_market` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_feedback_seller` FOREIGN KEY (`seller`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `seller_feeddback_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `seller_feedback_propkey`
--

DROP TABLE IF EXISTS `seller_feedback_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `seller_feedback_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `prettyname` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `seller_feedback_propval`
--

DROP TABLE IF EXISTS `seller_feedback_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `seller_feedback_propval` (
  `propkey` bigint(11) NOT NULL,
  `feedback` bigint(11) NOT NULL,
  `data` mediumtext,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  PRIMARY KEY (`propkey`,`feedback`),
  KEY `seller_feedback_propval_feedback_idx` (`feedback`),
  KEY `seller_feedback_propval_feedbackkey_index` (`feedback`,`propkey`),
  KEY `seller_feedback_propval_modifiedon_index` (`modified_on`),
  KEY `seller_feedback_propval_idx` (`scrape`),
  CONSTRAINT `seller_feedback_propkey_key` FOREIGN KEY (`propkey`) REFERENCES `seller_feedback_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_feedback_propval_feedback` FOREIGN KEY (`feedback`) REFERENCES `seller_feedback` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_feedback_propval_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER seller_feedback_propval_before_update_audit 
    BEFORE UPDATE ON seller_feedback_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `seller_feedback_propvalaudit`
			(`modified_on`, `feedback`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`feedback`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	ELSE
		IF OLD.`scrape` is not null
		THEN  
			SET NEW.scrape = OLD.scrape;
		END IF;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `seller_feedback_propvalaudit`
--

DROP TABLE IF EXISTS `seller_feedback_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `seller_feedback_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `feedback` bigint(11) NOT NULL,
  `data` mediumtext,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) NOT NULL,
  KEY `seller_feedback_propvalaudit_feedback_idx` (`feedback`),
  KEY `seller_feedback_propvalaudit_propkey_idx` (`propkey`),
  KEY `seller_feedback_propvalaudit_feedbackkey_index` (`feedback`,`propkey`),
  KEY `seller_feedback_propvalaudit_modifiedon_index` (`modified_on`),
  KEY `seller_feedback_propvalaudit_scrape_idx` (`scrape`),
  CONSTRAINT `seller_feedback_propvalaudit_feedback` FOREIGN KEY (`feedback`) REFERENCES `seller_feedback` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_feedback_propvalaudit_propkey` FOREIGN KEY (`propkey`) REFERENCES `seller_feedback_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_feedback_propvalaudit_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `market` bigint(11) NOT NULL,
  `username` varchar(150) DEFAULT NULL,
  `relativeurl` text,
  `fullurl` text,
  `scrape` bigint(11) NOT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `market_username` (`market`,`username`),
  KEY `seller_market_idx` (`market`),
  KEY `seller_scrape_idx` (`scrape`),
  CONSTRAINT `seller_market` FOREIGN KEY (`market`) REFERENCES `market` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `seller_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_propkey`
--

DROP TABLE IF EXISTS `user_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `prettyname` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_propval`
--

DROP TABLE IF EXISTS `user_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propval` (
  `propkey` bigint(11) NOT NULL,
  `user` bigint(11) NOT NULL,
  `data` mediumtext,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) NOT NULL,
  PRIMARY KEY (`propkey`,`user`),
  KEY `user_propval_user_idx` (`user`),
  KEY `user_propval_userkey_index` (`user`,`propkey`),
  KEY `user_propval_modifiedon_index` (`modified_on`),
  KEY `user_propval_scrape_idx` (`scrape`),
  CONSTRAINT `user_propkey_key` FOREIGN KEY (`propkey`) REFERENCES `user_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_propval_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_propval_user` FOREIGN KEY (`user`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;

DROP VIEW IF EXISTS `ads_view`;

create view `ads_view` (`id`, `external_id`, `pid`, `market`, `title`, `seller`, `relativeurl`, `fullurl`, `last_update`, `modified_on`, `scrape`)
as 
select  a.`id`, 
		a.`external_id`,
        concat(m.`spider`, '_', a.`external_id`),
        a.`market`,
        a.`title`,
        a.`seller`,
        a.`relativeurl`,
        a.`fullurl`,
        a.`last_update`,
        a.`modified_on`,
        a.`scrape`
from `ads` a 
join `market` m on a.`market` = m.`id`;

DROP VIEW IF EXISTS `ads_feedback_view`;

create view `ads_feedback_view` (`id`, `pid`, `market`, `ads`, `modified_on`, `scrape`, `hash`, `count`)
as
select	f.`id`,
		concat(m.`spider`, '_', a.`external_id`),
        f.`market`,
        f.`ads`,
        f.`modified_on`,
        f.`scrape`,
        f.`hash`,
        f.`count`
from `ads_feedback` f
join `ads` a on f.`ads` = a.`id`
join `market` m on f.`market` = m.`id`;

DROP VIEW IF EXISTS `user_view`;

create view `user_view` (`id`, `sid`, `market`, `username`, `relativeurl`, `fullurl`, `scrape`, `modified_on`)
as
select 	u.`id`,
		concat(m.`spider`, '_', u.`username`),
        u.`market`,
        u.`username`,
		u.`relativeurl`,
        u.`fullurl`,
        u.`scrape`,
        u.`modified_on`
from `user` u
join `market` m on u.`market`= m.`id`;

DROP VIEW IF EXISTS `seller_feedback_view`;

create view `seller_feedback_view` (`id`, `sid`, `market`, `seller`, `modified_on`, `scrape`, `hash`, `count`)
as
select	f.`id`,
		concat(m.`spider`, '_', u.`username`),
        f.`market`,
        f.`seller`,
        f.`modified_on`,
        f.`scrape`,
        f.`hash`,
        f.`count`
from `seller_feedback` f
join `user` u on f.`seller` = u.`id`
join `market` m on f.`market` = m.`id`;


/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER user_propval_before_update_audit 
    BEFORE UPDATE ON user_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `user_propvalaudit`
			(`modified_on`, `user`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`user`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	ELSE
		IF OLD.`scrape` is not null
		THEN  
			SET NEW.scrape = OLD.scrape;
		END IF;
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `user_propvalaudit`
--

DROP TABLE IF EXISTS `user_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `user` bigint(11) NOT NULL,
  `data` text,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) NOT NULL,
  KEY `user_propvalaudit_user_idx` (`user`),
  KEY `user_propvalaudit_propkey_idx` (`propkey`),
  KEY `user_propvalaudit_userkey_index` (`user`,`propkey`),
  KEY `user_user_propvalaudit_modifiedon_index` (`modified_on`),
  KEY `user_propvalaudit_scrape_idx` (`scrape`),
  CONSTRAINT `user_prophistory_propkey` FOREIGN KEY (`propkey`) REFERENCES `user_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_prophistory_user` FOREIGN KEY (`user`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_propvalaudit_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'markets'
--
/*!50003 DROP PROCEDURE IF EXISTS `delete_process` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` PROCEDURE `delete_process`(IN processid bigint(11))
BEGIN
	DECLARE n INT DEFAULT 0;
	DECLARE i INT DEFAULT 0;
	DECLARE scrapeid INT DEFAULT 0;
    
	DECLARE exit handler for sqlexception
	  BEGIN
	  
	  ROLLBACK;
	  RESIGNAL;
	END;

	DECLARE exit handler for sqlwarning
	 BEGIN
	 ROLLBACK;
	 RESIGNAL;
	END;

	set n = (select count(1) from `scrape` where `process`=processid);
    
	START TRANSACTION;
		
		while i < n do
			set scrapeid = (select `id` from `scrape` where `process`=processid limit 1);
			call delete_scrape(scrapeid);
            set i = i+1;
		end while;
		delete from `process` where `id` = processid;
	COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 DROP PROCEDURE IF EXISTS `delete_scrape` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` PROCEDURE `delete_scrape`(IN scrapeid bigint(11))
BEGIN

DECLARE exit handler for sqlexception
  BEGIN
  
  ROLLBACK;
  RESIGNAL;
END;

DECLARE exit handler for sqlwarning
 BEGIN
 ROLLBACK;
 RESIGNAL;
END;

START TRANSACTION;
	SET FOREIGN_KEY_CHECKS=0;
    
    delete from `seller_feedback_propvalaudit` where `scrape`=scrapeid;
    delete from `seller_feedback_propval` where `scrape`=scrapeid;
    delete from `seller_feedback` where `scrape`=scrapeid;
    
 	delete from `ads_feedback_propvalaudit` where `scrape`=scrapeid;
	delete from `ads_feedback_propval` where `scrape`=scrapeid;
	delete from `ads_feedback` where `scrape`=scrapeid;
    
    delete from `ads_img` where `scrape`=scrapeid;
    
	delete from `ads_propvalaudit` where `scrape`=scrapeid;
	delete from `ads_propval` where `scrape`=scrapeid;
	delete from `ads` where `scrape`=scrapeid;
    
    delete from `user_propvalaudit` where `scrape`=scrapeid;
	delete from `user_propval` where `scrape`=scrapeid;
	delete from `user` where `scrape`=scrapeid;
    
	delete from `scrapestat` where `scrape`=scrapeid;
	delete from `scrape` where `id`=scrapeid;
	SET FOREIGN_KEY_CHECKS=1;
COMMIT;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2017-07-09 23:30:48
