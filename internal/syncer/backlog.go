package syncer

import (
	"fmt"

	"github.com/andygrunwald/go-jira"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/jiraplus"
)

func (s *JiraSyncer) backlog(board *jira.Board, refs []string) error {
	if s.config.Mail.Path.Backlog == "" {
		return nil
	}

	logmsg := fmt.Sprintf("remote %q, board %q, backlog", s.remote, board.Name)
	logrus.Infof("%s begin to process", logmsg)

	mdir, err := Maildir(s.getPath(s.config.Mail.Path.Backlog))
	if err != nil {
		return err
	}

	msg, err := s.converter.Board(board, "nobody@jira", refs)
	if err != nil {
		return err
	}

	err = s.writeMessage(mdir, msg)
	if err != nil {
		return err
	}

	refs = append(refs, msg.Header.Get("Message-ID"))

	opts := &jiraplus.BoardIssuesSearchOptions{}
	opts.MaxResults = 100
	opts.Fields = []string{"*all"}

	count, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.PlusBoard.GetIssuesBacklog(board.ID, opts)
			if err != nil {
				return nil, err
			}

			if ret.Total <= i {
				return nil, nil
			}

			a := make([]interface{}, len(ret.Issues))

			for k := range ret.Issues {
				a[k] = ret.Issues[k]
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
	if err != nil {
		return err
	}

	logrus.Infof("%s, %d issues handled", logmsg, count)

	// Garbage collection
	err = s.CleanDir(mdir)
	if err != nil {
		return err
	}

	return nil
}
