package syncer

import (
	"path"

	"github.com/andygrunwald/go-jira"

	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/jiraplus"
	"github.com/legionus/jiramail/internal/maildir"
	"github.com/legionus/jiramail/internal/message"
)

func (s *JiraSyncer) issue(mdir maildir.Dir, issue *jira.Issue, refs []string) error {
	mailList, err := s.converter.Issue(issue, refs)
	if err != nil {
		return err
	}

	for _, msg := range mailList {
		prevmsg, err := s.readMessage(mdir, msg)
		if err != nil {
			return err
		}

		if prevmsg != nil && prevmsg.Meta != nil {
			for _, field := range prevmsg.Meta.Data {
				curv := msg.Meta.Get(field.Name, message.JiraNewColumn)
				prev := prevmsg.Meta.Get(field.Name, message.JiraNewColumn)
				if curv != prev {
					msg.Meta.Set(field.Name, message.JiraDiffColumn, "!")
				}
				msg.Meta.Set(field.Name, message.JiraPrevColumn, prev)
			}
		}

		err = s.writeMessage(mdir, msg)
		if err != nil {
			return err
		}
	}

	return nil
}

func (s *JiraSyncer) projectissue(issue *jira.Issue) error {
	mdir, err := Maildir(path.Join(s.config.Remote[s.remote].DestDir, "projects", issue.Fields.Project.Key))
	if err != nil {
		return err
	}
	s.projects[issue.Fields.Project.Key] = struct{}{}

	refs := []string{
		jiraconv.RemoteMessageID(s.remote),
		jiraconv.ProjectMessageID(&issue.Fields.Project),
	}

	return s.issue(mdir, issue, refs)
}

func (s *JiraSyncer) issues(mdir maildir.Dir, query string, refs []string) (int, error) {
	opts := &jira.SearchOptions{
		StartAt:    0,
		MaxResults: 100,
		Fields:     []string{"*all"},
	}

	return jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.Issue.Search(query, opts)
			if err != nil {
				return nil, err
			}

			a := make([]interface{}, len(ret))

			for k := range ret {
				a[k] = &ret[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			issue := o.(*jira.Issue)

			if issue.Fields == nil || issue.Fields.Type.Subtask {
				return nil
			}

			if err := s.issue(mdir, issue, refs); err != nil {
				return err
			}

			if err := s.projectissue(issue); err != nil {
				return err
			}

			return nil
		},
	)
}
