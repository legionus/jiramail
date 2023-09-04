# jiramail

 The `jiramail` is mail transport for Atlassian's Jira service. This utility
 stores data into mailbox.

My main desire is to use mutt to read jira tickets.

## Configuration

The utility uses a config file to store authentication information.

```toml
[jira]
server = "https://issues.redhat.com/"
auth = "token"
token = "<sometoken>"
```

## Usage

A few usage examples:

```
 jiramail.py --query "assignee = currentUser()" jira-my-issues.mbox
 jiramail.py --issue RHEL-123 rhel.mbox
```
