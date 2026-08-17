CREATE DATABASE  IF NOT EXISTS `compliance-letter-portal` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `compliance-letter-portal`;
-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: compliance-letter-portal
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accounts_department`
--

DROP TABLE IF EXISTS `accounts_department`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_department` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `code` varchar(20) NOT NULL,
  `description` longtext NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `head_id` bigint DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `code` (`code`),
  KEY `accounts_department_head_id_d5b22056_fk_accounts_user_id` (`head_id`),
  KEY `accounts_department_parent_id_1cf3cf29_fk_accounts_department_id` (`parent_id`),
  CONSTRAINT `accounts_department_head_id_d5b22056_fk_accounts_user_id` FOREIGN KEY (`head_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_department_parent_id_1cf3cf29_fk_accounts_department_id` FOREIGN KEY (`parent_id`) REFERENCES `accounts_department` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_loginaudit`
--

DROP TABLE IF EXISTS `accounts_loginaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_loginaudit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(150) NOT NULL,
  `ip_address` char(39) NOT NULL,
  `user_agent` longtext NOT NULL,
  `status` varchar(20) NOT NULL,
  `failure_reason` varchar(200) NOT NULL,
  `login_time` datetime(6) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_loginaudit_user_id_572318fe_fk_accounts_user_id` (`user_id`),
  KEY `accounts_lo_usernam_5bd900_idx` (`username`,`login_time` DESC),
  KEY `accounts_lo_ip_addr_72bbe8_idx` (`ip_address`),
  KEY `accounts_lo_status_fb291d_idx` (`status`),
  CONSTRAINT `accounts_loginaudit_user_id_572318fe_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_notification`
--

DROP TABLE IF EXISTS `accounts_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_notification` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type` varchar(50) NOT NULL,
  `title` varchar(200) NOT NULL,
  `message` longtext NOT NULL,
  `link` varchar(500) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `read_at` datetime(6) DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `expires_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_no_user_id_b37b35_idx` (`user_id`,`created_at` DESC),
  KEY `accounts_no_user_id_a4ff2e_idx` (`user_id`,`is_read`),
  KEY `accounts_no_expires_c7af83_idx` (`expires_at`),
  CONSTRAINT `accounts_notification_user_id_30e6cfc5_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=215 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_role`
--

DROP TABLE IF EXISTS `accounts_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `display_name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `is_system_role` tinyint(1) NOT NULL,
  `hierarchy_level` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_role_permissions`
--

DROP TABLE IF EXISTS `accounts_role_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_role_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_role_permissions_role_id_permission_id_032c715e_uniq` (`role_id`,`permission_id`),
  KEY `accounts_role_permis_permission_id_76fe677d_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_role_permis_permission_id_76fe677d_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_role_permissions_role_id_54f107a6_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_user`
--

DROP TABLE IF EXISTS `accounts_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `role` varchar(50) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `department` varchar(100) NOT NULL,
  `employee_id` varchar(50) NOT NULL,
  `job_title` varchar(100) NOT NULL,
  `email_verified` tinyint(1) NOT NULL,
  `phone_verified` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_locked` tinyint(1) NOT NULL,
  `lock_reason` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `last_activity` datetime(6) NOT NULL,
  `last_password_change` datetime(6) NOT NULL,
  `login_attempts` int NOT NULL,
  `two_factor_enabled` tinyint(1) NOT NULL,
  `session_key` varchar(100) NOT NULL,
  `managed_clients` json NOT NULL,
  `notification_preferences` json NOT NULL,
  `theme_preferences` json NOT NULL,
  `manager_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `employee_id` (`employee_id`),
  KEY `accounts_user_manager_id_57cc9038_fk_accounts_user_id` (`manager_id`),
  CONSTRAINT `accounts_user_manager_id_57cc9038_fk_accounts_user_id` FOREIGN KEY (`manager_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_user_groups`
--

DROP TABLE IF EXISTS `accounts_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_user_user_permissions`
--

DROP TABLE IF EXISTS `accounts_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_useractivitylog`
--

DROP TABLE IF EXISTS `accounts_useractivitylog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_useractivitylog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(50) NOT NULL,
  `model_name` varchar(100) NOT NULL,
  `object_id` varchar(100) NOT NULL,
  `object_repr` varchar(200) NOT NULL,
  `changes` json NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_us_user_id_39428d_idx` (`user_id`,`timestamp` DESC),
  KEY `accounts_us_action_ec31c8_idx` (`action`),
  KEY `accounts_us_model_n_4177fd_idx` (`model_name`),
  CONSTRAINT `accounts_useractivitylog_user_id_33f5b02a_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=190 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_userpreference`
--

DROP TABLE IF EXISTS `accounts_userpreference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_userpreference` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `default_dashboard` varchar(100) NOT NULL,
  `widget_layout` json NOT NULL,
  `email_notifications` tinyint(1) NOT NULL,
  `email_digest_frequency` varchar(20) NOT NULL,
  `items_per_page` int NOT NULL,
  `date_format` varchar(20) NOT NULL,
  `time_format` varchar(20) NOT NULL,
  `timezone` varchar(50) NOT NULL,
  `language` varchar(10) NOT NULL,
  `theme` varchar(20) NOT NULL,
  `sidebar_collapsed` tinyint(1) NOT NULL,
  `notification_sound` tinyint(1) NOT NULL,
  `desktop_notifications` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `accounts_userpreference_user_id_110cffd7_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_usersession`
--

DROP TABLE IF EXISTS `accounts_usersession`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_usersession` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_key` varchar(100) DEFAULT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `device_type` varchar(50) NOT NULL,
  `browser` varchar(100) NOT NULL,
  `operating_system` varchar(100) NOT NULL,
  `login_time` datetime(6) NOT NULL,
  `last_activity` datetime(6) NOT NULL,
  `logout_time` datetime(6) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_key` (`session_key`),
  KEY `accounts_usersession_user_id_567c9519_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `accounts_usersession_user_id_567c9519_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=126 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `common_auditlog`
--

DROP TABLE IF EXISTS `common_auditlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `common_auditlog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(50) NOT NULL,
  `model_name` varchar(100) NOT NULL,
  `object_id` varchar(100) NOT NULL,
  `object_repr` varchar(200) NOT NULL,
  `changes` json NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `common_auditlog_user_id_59bdef13_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `common_auditlog_user_id_59bdef13_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `documents_document`
--

DROP TABLE IF EXISTS `documents_document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents_document` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `document_type` varchar(50) NOT NULL,
  `pdf_file` varchar(100) DEFAULT NULL,
  `external_url` varchar(200) NOT NULL,
  `version` varchar(20) NOT NULL,
  `is_latest` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_public` tinyint(1) NOT NULL,
  `table_data` json NOT NULL,
  `display_order` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `category_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `documents_d_documen_c85bf6_idx` (`document_type`,`is_active`),
  KEY `documents_d_is_publ_56f406_idx` (`is_public`,`is_active`),
  KEY `documents_d_created_71dced_idx` (`created_at` DESC),
  KEY `documents_document_created_by_id_7d00c649_fk_accounts_user_id` (`created_by_id`),
  KEY `documents_document_category_id_99a4d66f_fk_documents` (`category_id`),
  KEY `documents_document_document_type_9c2f30c7` (`document_type`),
  CONSTRAINT `documents_document_category_id_99a4d66f_fk_documents` FOREIGN KEY (`category_id`) REFERENCES `documents_documentcategory` (`id`),
  CONSTRAINT `documents_document_created_by_id_7d00c649_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `documents_document_view_permissions`
--

DROP TABLE IF EXISTS `documents_document_view_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents_document_view_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `documents_document_view__document_id_user_id_54cd9707_uniq` (`document_id`,`user_id`),
  KEY `documents_document_v_user_id_925f9cd9_fk_accounts_` (`user_id`),
  CONSTRAINT `documents_document_v_document_id_be9dcfc3_fk_documents` FOREIGN KEY (`document_id`) REFERENCES `documents_document` (`id`),
  CONSTRAINT `documents_document_v_user_id_925f9cd9_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `documents_documentcategory`
--

DROP TABLE IF EXISTS `documents_documentcategory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents_documentcategory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `slug` varchar(50) NOT NULL,
  `description` longtext NOT NULL,
  `order` int NOT NULL,
  `icon` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `documents_documentversion`
--

DROP TABLE IF EXISTS `documents_documentversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents_documentversion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version` varchar(20) NOT NULL,
  `pdf_file` varchar(100) NOT NULL,
  `changelog` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `document_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `documents_documentve_created_by_id_aaa305f1_fk_accounts_` (`created_by_id`),
  KEY `documents_documentve_document_id_42757b7a_fk_documents` (`document_id`),
  CONSTRAINT `documents_documentve_created_by_id_aaa305f1_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `documents_documentve_document_id_42757b7a_fk_documents` FOREIGN KEY (`document_id`) REFERENCES `documents_document` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `documents_documentviewlog`
--

DROP TABLE IF EXISTS `documents_documentviewlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `documents_documentviewlog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(20) NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `document_id` bigint NOT NULL,
  `user_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `documents_documentvi_document_id_21b7ac80_fk_documents` (`document_id`),
  KEY `documents_documentviewlog_user_id_08989e3f_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `documents_documentvi_document_id_21b7ac80_fk_documents` FOREIGN KEY (`document_id`) REFERENCES `documents_document` (`id`),
  CONSTRAINT `documents_documentviewlog_user_id_08989e3f_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_artivaletters`
--

DROP TABLE IF EXISTS `letters_artivaletters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_artivaletters` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `letter_code` varchar(100) NOT NULL,
  `creation_type` varchar(20) NOT NULL,
  `creation_revision_date` datetime(6) NOT NULL,
  `communication_type` varchar(20) NOT NULL,
  `communication_code` varchar(50) NOT NULL,
  `timing` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `document_description` longtext NOT NULL,
  `production_date` date NOT NULL,
  `source` varchar(200) NOT NULL,
  `letter_description` longtext NOT NULL,
  `system_type` varchar(20) NOT NULL,
  `status` varchar(50) NOT NULL,
  `current_version` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `submitted_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `comments` longtext NOT NULL,
  `internal_notes` longtext NOT NULL,
  `created_by_id` bigint NOT NULL,
  `delegated_to_id` bigint DEFAULT NULL,
  `communication_subtype` varchar(20) NOT NULL,
  `regulatory` varchar(10) NOT NULL,
  `ticket_completed_date` datetime(6) DEFAULT NULL,
  `ticket_number` varchar(100) NOT NULL,
  `ticket_open_date` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `letter_code` (`letter_code`),
  KEY `letters_artivaletters_created_by_id_471fe9cf_fk_accounts_user_id` (`created_by_id`),
  KEY `letters_artivaletter_delegated_to_id_31aed2b9_fk_accounts_` (`delegated_to_id`),
  KEY `letters_art_regulat_b68d9c_idx` (`regulatory`),
  KEY `letters_art_timing_d4e1ad_idx` (`timing`),
  KEY `letters_art_source_f798d3_idx` (`source`),
  CONSTRAINT `letters_artivaletter_delegated_to_id_31aed2b9_fk_accounts_` FOREIGN KEY (`delegated_to_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_artivaletters_created_by_id_471fe9cf_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=113 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_auditlog`
--

DROP TABLE IF EXISTS `letters_auditlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_auditlog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `action` varchar(50) NOT NULL,
  `changes` json NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `content_type_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `letters_auditlog_content_type_id_c9af0841_fk_django_co` (`content_type_id`),
  KEY `letters_aud_action_fcbd60_idx` (`action`),
  KEY `letters_aud_timesta_36797f_idx` (`timestamp`),
  KEY `letters_aud_user_id_d7a1f4_idx` (`user_id`),
  CONSTRAINT `letters_auditlog_content_type_id_c9af0841_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_auditlog_user_id_8744f8bc_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_auditlog_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_comment`
--

DROP TABLE IF EXISTS `letters_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_comment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `text` longtext NOT NULL,
  `is_internal` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `author_id` bigint NOT NULL,
  `content_type_id` int NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `letters_comment_content_type_id_ac601b81_fk_django_co` (`content_type_id`),
  KEY `letters_comment_parent_id_146e84e0_fk_letters_comment_id` (`parent_id`),
  KEY `letters_com_created_f02ddd_idx` (`created_at`),
  KEY `letters_com_author__b0affd_idx` (`author_id`),
  CONSTRAINT `letters_comment_author_id_cd19433e_fk_accounts_user_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_comment_content_type_id_ac601b81_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_comment_parent_id_146e84e0_fk_letters_comment_id` FOREIGN KEY (`parent_id`) REFERENCES `letters_comment` (`id`),
  CONSTRAINT `letters_comment_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_documentattachment`
--

DROP TABLE IF EXISTS `letters_documentattachment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_documentattachment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `file` varchar(100) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `file_size` int unsigned NOT NULL,
  `file_type` varchar(50) NOT NULL,
  `document_type` varchar(50) NOT NULL,
  `description` longtext NOT NULL,
  `upload_date` datetime(6) NOT NULL,
  `is_current` tinyint(1) NOT NULL,
  `download_count` int unsigned NOT NULL,
  `content_type_id` int NOT NULL,
  `uploaded_by_id` bigint NOT NULL,
  `version_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `letters_doc_documen_7d0422_idx` (`document_type`),
  KEY `letters_doc_upload__abb8b5_idx` (`upload_date`),
  KEY `letters_doc_is_curr_80c587_idx` (`is_current`),
  KEY `letters_documentatta_content_type_id_4caec729_fk_django_co` (`content_type_id`),
  KEY `letters_documentatta_uploaded_by_id_d99a0397_fk_accounts_` (`uploaded_by_id`),
  KEY `letters_documentatta_version_id_cfcc476f_fk_letters_l` (`version_id`),
  CONSTRAINT `letters_documentatta_content_type_id_4caec729_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_documentatta_uploaded_by_id_d99a0397_fk_accounts_` FOREIGN KEY (`uploaded_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_documentatta_version_id_cfcc476f_fk_letters_l` FOREIGN KEY (`version_id`) REFERENCES `letters_letterversion` (`id`),
  CONSTRAINT `letters_documentattachment_chk_1` CHECK ((`object_id` >= 0)),
  CONSTRAINT `letters_documentattachment_chk_2` CHECK ((`file_size` >= 0)),
  CONSTRAINT `letters_documentattachment_chk_3` CHECK ((`download_count` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=140 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_facsletters`
--

DROP TABLE IF EXISTS `letters_facsletters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_facsletters` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `letter_code` varchar(100) NOT NULL,
  `creation_type` varchar(20) NOT NULL,
  `creation_revision_date` datetime(6) NOT NULL,
  `communication_type` varchar(20) NOT NULL,
  `communication_code` varchar(50) NOT NULL,
  `timing` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `document_description` longtext NOT NULL,
  `production_date` date NOT NULL,
  `source` varchar(200) NOT NULL,
  `letter_description` longtext NOT NULL,
  `system_type` varchar(20) NOT NULL,
  `status` varchar(50) NOT NULL,
  `current_version` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `submitted_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `comments` longtext NOT NULL,
  `internal_notes` longtext NOT NULL,
  `client_approvals` json NOT NULL,
  `created_by_id` bigint NOT NULL,
  `delegated_to_id` bigint DEFAULT NULL,
  `communication_subtype` varchar(20) NOT NULL,
  `regulatory` varchar(10) NOT NULL,
  `ticket_completed_date` datetime(6) DEFAULT NULL,
  `ticket_number` varchar(100) NOT NULL,
  `ticket_open_date` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `letter_code` (`letter_code`),
  KEY `letters_facsletters_created_by_id_3590d644_fk_accounts_user_id` (`created_by_id`),
  KEY `letters_facsletters_delegated_to_id_24a221db_fk_accounts_user_id` (`delegated_to_id`),
  KEY `letters_fac_regulat_307578_idx` (`regulatory`),
  KEY `letters_fac_timing_ebdfee_idx` (`timing`),
  KEY `letters_fac_source_1a615a_idx` (`source`),
  CONSTRAINT `letters_facsletters_created_by_id_3590d644_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_facsletters_delegated_to_id_24a221db_fk_accounts_user_id` FOREIGN KEY (`delegated_to_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_historicalartivaletters`
--

DROP TABLE IF EXISTS `letters_historicalartivaletters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_historicalartivaletters` (
  `id` bigint NOT NULL,
  `letter_code` varchar(100) NOT NULL,
  `creation_type` varchar(20) NOT NULL,
  `creation_revision_date` datetime(6) NOT NULL,
  `communication_type` varchar(20) NOT NULL,
  `communication_code` varchar(50) NOT NULL,
  `timing` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `document_description` longtext NOT NULL,
  `production_date` date NOT NULL,
  `source` varchar(200) NOT NULL,
  `letter_description` longtext NOT NULL,
  `system_type` varchar(20) NOT NULL,
  `status` varchar(50) NOT NULL,
  `current_version` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `submitted_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `comments` longtext NOT NULL,
  `internal_notes` longtext NOT NULL,
  `history_id` int NOT NULL AUTO_INCREMENT,
  `history_date` datetime(6) NOT NULL,
  `history_change_reason` varchar(100) DEFAULT NULL,
  `history_type` varchar(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `delegated_to_id` bigint DEFAULT NULL,
  `history_user_id` bigint DEFAULT NULL,
  `communication_subtype` varchar(20) NOT NULL,
  `regulatory` varchar(10) NOT NULL,
  `ticket_completed_date` datetime(6) DEFAULT NULL,
  `ticket_number` varchar(100) NOT NULL,
  `ticket_open_date` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`history_id`),
  KEY `letters_historicalar_history_user_id_1381ec09_fk_accounts_` (`history_user_id`),
  KEY `letters_historicalartivaletters_id_b1b045e6` (`id`),
  KEY `letters_historicalartivaletters_letter_code_a957c014` (`letter_code`),
  KEY `letters_historicalartivaletters_history_date_4e95c7c7` (`history_date`),
  KEY `letters_historicalartivaletters_created_by_id_044a341e` (`created_by_id`),
  KEY `letters_historicalartivaletters_delegated_to_id_cb46d401` (`delegated_to_id`),
  CONSTRAINT `letters_historicalar_history_user_id_1381ec09_fk_accounts_` FOREIGN KEY (`history_user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=109 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_historicalfacsletters`
--

DROP TABLE IF EXISTS `letters_historicalfacsletters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_historicalfacsletters` (
  `id` bigint NOT NULL,
  `letter_code` varchar(100) NOT NULL,
  `creation_type` varchar(20) NOT NULL,
  `creation_revision_date` datetime(6) NOT NULL,
  `communication_type` varchar(20) NOT NULL,
  `communication_code` varchar(50) NOT NULL,
  `timing` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `document_description` longtext NOT NULL,
  `production_date` date NOT NULL,
  `source` varchar(200) NOT NULL,
  `letter_description` longtext NOT NULL,
  `system_type` varchar(20) NOT NULL,
  `status` varchar(50) NOT NULL,
  `current_version` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `submitted_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `comments` longtext NOT NULL,
  `internal_notes` longtext NOT NULL,
  `client_approvals` json NOT NULL,
  `history_id` int NOT NULL AUTO_INCREMENT,
  `history_date` datetime(6) NOT NULL,
  `history_change_reason` varchar(100) DEFAULT NULL,
  `history_type` varchar(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `delegated_to_id` bigint DEFAULT NULL,
  `history_user_id` bigint DEFAULT NULL,
  `communication_subtype` varchar(20) NOT NULL,
  `regulatory` varchar(10) NOT NULL,
  `ticket_completed_date` datetime(6) DEFAULT NULL,
  `ticket_number` varchar(100) NOT NULL,
  `ticket_open_date` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`history_id`),
  KEY `letters_historicalfa_history_user_id_06a7bd45_fk_accounts_` (`history_user_id`),
  KEY `letters_historicalfacsletters_id_f17cea5e` (`id`),
  KEY `letters_historicalfacsletters_letter_code_edca46f2` (`letter_code`),
  KEY `letters_historicalfacsletters_history_date_dee1ca7f` (`history_date`),
  KEY `letters_historicalfacsletters_created_by_id_9894cd48` (`created_by_id`),
  KEY `letters_historicalfacsletters_delegated_to_id_35e4e8e8` (`delegated_to_id`),
  CONSTRAINT `letters_historicalfa_history_user_id_06a7bd45_fk_accounts_` FOREIGN KEY (`history_user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=193 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_letterversion`
--

DROP TABLE IF EXISTS `letters_letterversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_letterversion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `version_number` varchar(10) NOT NULL,
  `version_date` datetime(6) NOT NULL,
  `version_note` longtext NOT NULL,
  `version_data` json NOT NULL,
  `changes_from_previous` longtext NOT NULL,
  `revision_reason` varchar(200) NOT NULL,
  `pdf_copy` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `content_type_id` int NOT NULL,
  `version_author_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `letters_letterversion_content_type_id_object_i_857df54e_uniq` (`content_type_id`,`object_id`,`version_number`),
  KEY `letters_let_version_0ef58b_idx` (`version_number`),
  KEY `letters_let_version_c34d2e_idx` (`version_date`),
  KEY `letters_letterversio_version_author_id_ae47cb66_fk_accounts_` (`version_author_id`),
  CONSTRAINT `letters_letterversio_content_type_id_05a81b42_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_letterversio_version_author_id_ae47cb66_fk_accounts_` FOREIGN KEY (`version_author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_letterversion_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_radiusapproval`
--

DROP TABLE IF EXISTS `letters_radiusapproval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_radiusapproval` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `approval_status` varchar(20) NOT NULL,
  `approval_date` datetime(6) DEFAULT NULL,
  `comments` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `cco_or_representative_id` bigint DEFAULT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `letters_radiusapproval_content_type_id_object_id_400aaab1_uniq` (`content_type_id`,`object_id`),
  KEY `letters_rad_approva_268baf_idx` (`approval_status`),
  KEY `letters_rad_approva_f14d2f_idx` (`approval_date`),
  KEY `letters_radiusapprov_cco_or_representativ_167ca7d7_fk_accounts_` (`cco_or_representative_id`),
  CONSTRAINT `letters_radiusapprov_cco_or_representativ_167ca7d7_fk_accounts_` FOREIGN KEY (`cco_or_representative_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_radiusapprov_content_type_id_e2ce0ab7_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_radiusapproval_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=153 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_sessionsapproval`
--

DROP TABLE IF EXISTS `letters_sessionsapproval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_sessionsapproval` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `approval_status` varchar(20) NOT NULL,
  `approval_date` datetime(6) DEFAULT NULL,
  `session_reference` varchar(100) NOT NULL,
  `comments` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `letters_sessionsapproval_content_type_id_object_id_81f46320_uniq` (`content_type_id`,`object_id`),
  KEY `letters_ses_approva_aa5df5_idx` (`approval_status`),
  KEY `letters_ses_approva_e9eb27_idx` (`approval_date`),
  CONSTRAINT `letters_sessionsappr_content_type_id_6dee62b9_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_sessionsapproval_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=147 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `letters_ticket`
--

DROP TABLE IF EXISTS `letters_ticket`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `letters_ticket` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `ticket_number` varchar(100) NOT NULL,
  `open_date` datetime(6) NOT NULL,
  `completed_date` datetime(6) DEFAULT NULL,
  `status` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `notes` longtext NOT NULL,
  `resolution_notes` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `assigned_to_id` bigint DEFAULT NULL,
  `content_type_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ticket_number` (`ticket_number`),
  KEY `letters_tic_ticket__c65945_idx` (`ticket_number`),
  KEY `letters_tic_status_1549c3_idx` (`status`),
  KEY `letters_tic_open_da_966d58_idx` (`open_date`),
  KEY `letters_ticket_assigned_to_id_2ed10e33_fk_accounts_user_id` (`assigned_to_id`),
  KEY `letters_ticket_content_type_id_f2f32ecc_fk_django_co` (`content_type_id`),
  CONSTRAINT `letters_ticket_assigned_to_id_2ed10e33_fk_accounts_user_id` FOREIGN KEY (`assigned_to_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `letters_ticket_content_type_id_f2f32ecc_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `letters_ticket_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-17 10:00:14
