-- TaxDesk schema.
-- Foreign key enforcement is per connection in SQLite, a PRAGMA in this
-- file would not stick. The code that opens the database must run
-- PRAGMA foreign_keys = ON on every connection.

CREATE TABLE CLIENTS(
    ID INTEGER PRIMARY KEY,
    NAME TEXT NOT NULL,
    -- the folder is a client's identity on disk, two clients can never share one
    FOLDER_PATH TEXT NOT NULL UNIQUE
);

CREATE TABLE SERVICES(
    ID INTEGER PRIMARY KEY,
    NAME TEXT NOT NULL UNIQUE
);

CREATE TABLE CLIENT_SERVICES(
    CLIENT_ID INTEGER NOT NULL,
    SERVICE_ID INTEGER NOT NULL,
    -- switching a service off must keep history, off is a flag, never a delete
    ACTIVE INTEGER NOT NULL DEFAULT 1 CHECK (ACTIVE IN (0, 1)),
    PRIMARY KEY (CLIENT_ID, SERVICE_ID),
    FOREIGN KEY (CLIENT_ID) REFERENCES CLIENTS(ID),
    FOREIGN KEY (SERVICE_ID) REFERENCES SERVICES(ID)
);

CREATE TABLE PERIODS(
    YEAR INTEGER NOT NULL CHECK (YEAR BETWEEN 2000 AND 2100),
    MONTH INTEGER NOT NULL CHECK (MONTH BETWEEN 1 AND 12),
    STATE TEXT NOT NULL DEFAULT 'open' CHECK (STATE IN ('open', 'closed')),
    PRIMARY KEY (YEAR, MONTH)
);

CREATE TABLE TASKS(
    ID INTEGER PRIMARY KEY,
    CLIENT_ID INTEGER NOT NULL,
    SERVICE_ID INTEGER NOT NULL,
    PERIOD_YEAR INTEGER NOT NULL,
    PERIOD_MONTH INTEGER NOT NULL,
    STATUS TEXT NOT NULL DEFAULT 'pending'
        CHECK (STATUS IN ('pending', 'done', 'not_applicable')),
    -- nullable on purpose, real due days are unknown until dad confirms them
    DUE_DATE TEXT,
    COMPLETED_AT TEXT,
    COMPLETION_METHOD TEXT,
    -- the core product rule, one client, one service, one month, at most one task
    UNIQUE (CLIENT_ID, SERVICE_ID, PERIOD_YEAR, PERIOD_MONTH),
    FOREIGN KEY (CLIENT_ID) REFERENCES CLIENTS(ID),
    FOREIGN KEY (SERVICE_ID) REFERENCES SERVICES(ID),
    FOREIGN KEY (PERIOD_YEAR, PERIOD_MONTH) REFERENCES PERIODS(YEAR, MONTH)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    -- every document belongs to a client, search by client depends on this
    client_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES CLIENTS(ID)
);
