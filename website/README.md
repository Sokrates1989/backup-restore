# Backup Manager Website

This is the web interface for the Backup Manager application.

## Structure

```
website/
├── index.html                    # Main application layout
├── app.js                        # Main application JavaScript
├── styles.css                    # Global styles
├── styles/tabs.css               # Tab-specific styles
├── databases/
│   ├── databases.html            # Databases tab HTML
│   └── databases.js              # Databases functionality
├── remote-storage-locations/
│   ├── remote-storage-locations.html # Remote Storage Locations tab HTML
│   └── remote-storage-locations.js  # Remote Storage Locations functionality
├── backup-schedules/
│   ├── backup-schedules.html     # Backup Schedules tab HTML
│   └── backup-schedules.js      # Backup Schedules functionality
└── backup-files/
    ├── backup-files.html         # Backup Files tab HTML
    └── backup-files.js          # Backup Files functionality
```

## Features

- **Databases**: Manage database connections for backup sources
- **Remote Storage Locations**: Configure storage destinations (local, SFTP, Google Drive)
- **Backup Schedules**: Set up automated backup schedules
- **Backup Files**: View, download, restore, and delete backup files

## Tab Naming Convention

- **Databases**: Database sources to backup from/restore to
- **Remote Storage Locations**: Remote locations to store backups to/restore from
- **Backup Schedules**: Automated backup schedules
- **Backup Files**: Available backup files (local and from remote storage)

## Development

The application uses a modular structure where each tab has its own HTML and JavaScript files. The main `app.js` handles:

- Authentication
- Tab loading and navigation
- Global state management
- API communication

Each tab's JavaScript file handles:
- Tab-specific UI rendering
- Form handling
- API calls for that tab's functionality
- Event listeners for tab elements

## API Endpoints

The application communicates with the backend API using the following endpoints:

- `/automation/targets` - Database management
- `/automation/destinations` - Remote storage location management
- `/automation/schedules` - Backup schedule management
- `/automation/runs` - Backup run history
- `/backup/files` - Local backup files
- `/backup/download/{filename}` - Download backup files
- `/backup/restore/{filename}` - Restore from backup
