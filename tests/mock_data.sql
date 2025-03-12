# This is only used to verify the parity with the legacy renderer

-- Insert data into evealliances table
INSERT INTO evealliances (id, color, name) VALUES
(1, '#FF0000', 'Alliance Red'),
(2, '#00FF00', 'Alliance Green'),
(3, '#0000FF', 'Alliance Blue'),
(4, '#FFFF00', 'Alliance Yellow');

-- Insert data into mapsolarsystems table
INSERT INTO mapsolarsystems (solarSystemID, solarSystemName, constellationID, regionID, x, y, z, station, sovPower, allianceID) VALUES
(100, 'System A', 10, 1, 0.0, 0.0, 0.0, TRUE, 5.0, 1),
(101, 'System B', 10, 1, 1.0, 0.0, 1.0, FALSE, 3.0, 2),
(102, 'System C', 11, 1, 2.0, 0.0, 2.0, TRUE, 4.0, 3),
(103, 'System D', 11, 2, 3.0, 0.0, 3.0, FALSE, 2.0, 1),
(104, 'System E', 12, 2, 4.0, 0.0, 4.0, TRUE, 6.0, 4),
(105, 'System F', 12, 2, 5.0, 0.0, 0.0, FALSE, 2.0, 3);
#(106, 'System G', 12, 2, 12.0, 0.0, 0.0, FALSE, 2.0, 3),
#(107, 'System H', 12, 2, NULL, NULL, NULL, FALSE, 2.0, 3);

-- Insert data into mapsolarsystemjumps table
INSERT INTO mapsolarsystemjumps (fromSolarSystemID, toSolarSystemID) VALUES
(100, 101),
(101, 102),
(102, 103),
(103, 104),
(104, 105),
(105, 100),
(100, 102),
(101, 103),
(102, 104),
(103, 105),
(104, 100),
(105, 101),

(101, 100),
(102, 101),
(103, 102),
(104, 103),
(105, 104),
(100, 105),
(102, 100),
(103, 101),
(104, 102),
(105, 103),
(100, 104),
(101, 105);
#(100, 106),
#(106, 107),
#(107, 100);

-- Insert data into mapregions table
INSERT INTO mapregions (regionID, regionName, x, y, z) VALUES
(1, 'Region Alpha', 0.0, 0.0, 0.0),
(2, 'Region Beta', 4.0, 0.0, 4.0),
(3, 'Region Gamma', 12.0, 0.0, 0.0),
(4, 'Region Delta', NULL, NULL, NULL);

-- Insert data into sovchangelog table
INSERT INTO sovchangelog (fromAllianceID, toAllianceID, systemID, sovPower) VALUES
(1, 2, 100, 5.0),
(2, 3, 101, 3.0),
(3, 1, 102, 4.0),
(1, 4, 103, 2.0),
(4, 2, 104, 6.0);
