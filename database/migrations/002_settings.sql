-- Application configuration, exactly one row by design. The CHECK on
-- ID makes a second row impossible. Configuration here is a typed
-- declaration of the values the product actually has, adding a future
-- value is a migration adding a column, never a loose key value row.
-- No row at all means the app is not configured yet, onboarding
-- creates the row when the practitioner picks the root folder.
CREATE TABLE SETTINGS (
    ID INTEGER PRIMARY KEY CHECK (ID = 1),
    ROOT_FOLDER TEXT NOT NULL
);
