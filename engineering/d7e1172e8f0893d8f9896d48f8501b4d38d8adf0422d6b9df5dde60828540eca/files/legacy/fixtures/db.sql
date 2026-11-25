CREATE TABLE runs(id INTEGER, model TEXT, quant TEXT, quality REAL, status TEXT, seconds REAL);
INSERT INTO runs VALUES (1,'A','Q4',81,'validated',550),(2,'A','Q4',85,'validated',600),(3,'A','Q4',99,'exploratory',400),(4,'B','Q8',90,'validated',900),(5,'B','Q8',NULL,'incomplete',NULL);
