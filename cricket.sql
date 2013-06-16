CREATE TABLE `matchresults` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `odi` int(6) NOT NULL,
  `team` char(32) NOT NULL,
  `vsteam` char(32) NOT NULL, 
  `score` int(4),
  `overs` int(3),
  `inns` int(1), 
  `result` char(12),
  `at` datetime,
  `ground` varchar(32),
  `url` varchar(128),
  PRIMARY KEY (`id`),
  UNIQUE KEY `odi_team` (`odi`, `team`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
CREATE TABLE `scorecard` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `odi` int(6) NOT NULL,
  `team` char(32) NOT NULL,
  `player` char(64) NOT NULL,
  `inns` int(1),
  `runs` int(4),
  `balls` int(4),
  `mins` int(4),
  `fours` int(4),
  `sixes` int(4),
  `pos` int(2),
  `dismissal` char(32),
  PRIMARY KEY (`id`),
  UNIQUE KEY `odi_team_player` (`odi`, `team`, `player`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
