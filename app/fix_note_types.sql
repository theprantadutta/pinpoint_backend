-- Fix existing note types in the database
-- Convert display names to database enum values

UPDATE notes SET note_type = 'text' WHERE note_type = 'Title Content';
UPDATE notes SET note_type = 'audio' WHERE note_type = 'Record Audio';
UPDATE notes SET note_type = 'todo' WHERE note_type = 'Todo List';
UPDATE notes SET note_type = 'reminder' WHERE note_type = 'Reminder';

-- Also handle any other legacy formats
UPDATE notes SET note_type = 'text' WHERE note_type NOT IN ('text', 'audio', 'todo', 'reminder');

SELECT 'Migration completed. Note types have been updated.' as result;
SELECT note_type, COUNT(*) as count FROM notes GROUP BY note_type;
