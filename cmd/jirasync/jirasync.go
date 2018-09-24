package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime/debug"
	"sync"
	"syscall"
	"time"

	"github.com/sevlyar/go-daemon"
	"github.com/sirupsen/logrus"

	"github.com/legionus/getopt"
	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/syncer"
)

var (
	prog           = ""
	version        = ""
	showVersionOpt = false
	showHelpOpt    = false
	lockDir        = ""
	exitCode       = 0
)

func usage() {
	fmt.Fprintf(os.Stdout, `
Usage: %[1]s [options]

This utility synchronizes the state of jira with local maildir.

Options:
  -f, --foreground       stay in the foreground;
  -1, --onesync          run synchronization once and exit;
  -c, --config=FILE      use an alternative configuration file;
  -V, --version          print program version and exit;
  -h, --help             show this text and exit.

Report bugs to author.

`,
		prog)
	os.Exit(0)
}

func showUsage(*getopt.Option, getopt.NameType, string) error {
	usage()
	return nil
}

func showVersion(*getopt.Option, getopt.NameType, string) error {
	fmt.Fprintf(os.Stdout, `%s version %s
Written by Alexey Gladkov.

Copyright (C) 2018  Alexey Gladkov <gladkov.alexey@gmail.com>
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

`,
		prog, version)
	os.Exit(0)
	return nil
}

func unlock() {
	if len(lockDir) > 0 {
		_ = os.RemoveAll(lockDir)
	}
}

func panicHandler() {
	r := recover()

	if r != nil {
		logrus.Errorf("panic: %s", r)
		debug.PrintStack()
		unlock()
		os.Exit(1)
	}
}

func defaultSigHandler(sig os.Signal) error {
	logrus.Infof("got signal %s, exit", sig)
	unlock()
	os.Exit(exitCode)
	return daemon.ErrStop
}

func main() {
	prog = filepath.Base(os.Args[0])
	configFile := os.Getenv("HOME") + "/.jiramailrc"

	var (
		logLevel   *logrus.Level
		oneSync    bool
		foreground bool
	)

	opts := &getopt.Getopt{
		AllowAbbrev: true,
		Options: []getopt.Option{
			{'h', "help", getopt.NoArgument,
				showUsage,
			},
			{'V', "version", getopt.NoArgument,
				showVersion,
			},
			{'c', "config", getopt.RequiredArgument,
				func(o *getopt.Option, t getopt.NameType, v string) (err error) {
					info, err := os.Stat(v)
					if err != nil {
						return
					}
					if !info.Mode().IsRegular() {
						return fmt.Errorf("regular file required")
					}
					configFile = v
					return
				},
			},
			{'l', "loglevel", getopt.RequiredArgument,
				func(o *getopt.Option, t getopt.NameType, v string) (err error) {
					lvl, err := logrus.ParseLevel(v)
					if err == nil {
						logLevel = &lvl
					}
					return
				},
			},
			{'f', "foreground", getopt.NoArgument,
				func(o *getopt.Option, t getopt.NameType, v string) (err error) {
					foreground = true
					return
				},
			},
			{'1', "onesync", getopt.NoArgument,
				func(o *getopt.Option, t getopt.NameType, v string) (err error) {
					oneSync = true
					return
				},
			},
		},
	}

	prog = filepath.Base(os.Args[0])
	if err := opts.Parse(os.Args); err != nil {
		logrus.Errorf("%v", err)
		return
	}

	if !foreground && !oneSync {
		ctx := &daemon.Context{
			WorkDir: "/",
		}

		child, err := ctx.Reborn()
		if err != nil {
			logrus.Errorf("%s", err)
		}
		if child != nil {
			return
		}
		defer ctx.Release()
	}

	cfg, err := config.Read(configFile)
	if err != nil {
		logrus.Errorf("%s", err)
		return
	}

	if logLevel != nil {
		logrus.SetLevel(*logLevel)
	} else {
		logrus.SetLevel(cfg.Core.LogLevel.Level)
	}

	logrus.SetFormatter(&logrus.TextFormatter{
		FullTimestamp:    true,
		DisableTimestamp: false,
	})

	if oneSync {
		err = syncer.SyncAll(cfg)
		if err != nil {
			logrus.Errorf("sync failed: %s", err)
		}
		return
	}

	if len(cfg.Core.LockDir) > 0 {
		err = os.Mkdir(cfg.Core.LockDir, 0700)
		if err != nil {
			if !os.IsExist(err) {
				logrus.Errorf("unable to create lock directory: %s", err)
			}
			logrus.Debugf("lock directory is already exists: %s", cfg.Core.LockDir)
			return
		}
		defer func() {
			_ = os.RemoveAll(cfg.Core.LockDir)
		}()
		lockDir = cfg.Core.LockDir
	}

	if !foreground && len(cfg.Core.LogFile) > 0 {
		f, err := os.OpenFile(cfg.Core.LogFile, os.O_WRONLY|os.O_APPEND|os.O_SYNC|os.O_CREATE, 0644)
		if err != nil {
			logrus.Errorf("unable to open log file: %s", err)
			return
		}
		defer f.Close()
		logrus.SetOutput(f)
	}

	daemon.SetSigHandler(defaultSigHandler, syscall.SIGINT, syscall.SIGHUP, syscall.SIGQUIT, syscall.SIGTERM)

	var wg sync.WaitGroup

	wg.Add(1)
	go func(c *config.Configuration) {
		defer wg.Done()
		defer panicHandler()

		err := daemon.ServeSignals()
		if err != nil {
			logrus.Errorf("serve signals failed: %s", err)
		}
	}(cfg)

	go func(c *config.Configuration) {
		defer wg.Done()
		defer panicHandler()

		ticker := time.NewTicker(c.Core.SyncPeriod)
		defer ticker.Stop()

		for {
			err := syncer.SyncAll(c)
			if err != nil {
				logrus.Errorf("sync failed: %s", err)
			}
			<-ticker.C
		}
	}(cfg)

	wg.Wait()
}
